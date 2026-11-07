"""Failure handling and boundary checks: module crashes, timeouts, contract violations, concurrency."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from app.core import stubs
from app.core.config import REPO_ROOT, Settings
from app.core.schemas import (
    ErrorResponse,
    Evidence,
    Investigation,
    MemoryStatus,
    MetricStatus,
    RecalledMemory,
    ResetResult,
)
from tests.conftest import tiny_dataset
from tests.integration.test_flow import BODY, load, run


def investigate(client, **over) -> dict:
    load(client)
    r = run(client, **over)
    assert r.status_code == 201, r.text
    return r.json()


def good_explain(analysis, context):
    return stubs.explain(analysis, context)


# --- explanation failures degrade; the calculated result is still returned ---


def test_explain_crash_returns_labeled_fallback(make_client):
    def boom(analysis, context):
        raise RuntimeError("secret-token-123 in the message")

    inv = investigate(make_client(explain=boom))
    expl = inv["explanation"]
    assert expl["validation_error_codes"] == ["explain_failed"]
    assert expl["explanation_source"] == "template" and expl["memory_status"] == "unavailable"
    assert expl["recommendations"] == []
    assert "secret-token" not in json.dumps(inv)  # exception text never reaches the response


def test_explain_timeout_returns_fallback(make_client):
    def slow(analysis, context):
        time.sleep(0.5)
        return stubs.explain(analysis, context)

    inv = investigate(make_client({"explain_timeout_seconds": 0.05}, explain=slow))
    assert inv["explanation"]["validation_error_codes"] == ["explain_timeout"]


def test_explain_malformed_output_returns_fallback(make_client):
    inv = investigate(make_client(explain=lambda a, c: {"summary": "only this"}))
    assert inv["explanation"]["validation_error_codes"] == ["explain_invalid_output"]


def _explanation_with(**changes):
    def explain(analysis, context):
        base = stubs.explain(analysis, context)
        rec = base.recommendations[0].model_copy(update=changes.pop("rec", {}))
        return base.model_copy(update={"recommendations": [rec], "validation_error_codes": [], **changes})

    return explain


def _recalled(event_time="2026-01-01T00:00:00Z"):
    return RecalledMemory(
        id="mem-1",
        memory_type="decision",
        event_time=event_time,
        incident_id=None,
        summary="Earlier decision",
    )


def test_future_recalled_memory_is_rejected(make_client):
    explain = _explanation_with(
        recalled=[_recalled("2026-12-01T00:00:00Z")], rec={"history_influence": ["mem-1"]}
    )
    inv = investigate(make_client(explain=explain))
    assert "future_recalled_memory" in inv["explanation"]["validation_error_codes"]
    assert inv["explanation"]["recalled"] == []


def test_valid_recalled_memory_passes(make_client):
    explain = _explanation_with(recalled=[_recalled()], rec={"history_influence": ["mem-1"]})
    inv = investigate(make_client(explain=explain))
    assert inv["explanation"]["validation_error_codes"] == []
    assert inv["explanation"]["recommendations"][0]["history_influence"] == ["mem-1"]


def test_unknown_citations_are_rejected(make_client):
    explain = _explanation_with(rec={"history_influence": ["ghost"], "evidence_ids": ["ghost-evidence"]})
    codes = investigate(make_client(explain=explain))["explanation"]["validation_error_codes"]
    assert codes == ["unknown_evidence_citation", "unknown_memory_citation"]


def test_memory_used_while_off_is_rejected(make_client):
    explain = _explanation_with(recalled=[_recalled()], rec={"history_influence": ["mem-1"]})
    inv = investigate(make_client(explain=explain), memory_mode="off")
    assert inv["explanation"]["validation_error_codes"] == ["memory_used_while_off"]


# --- analysis violations are bugs and fail loudly ---


def _analysis_with(**changes):
    def analyze(dataset, policy_id, as_of):
        base = stubs.analyze(dataset, policy_id, as_of)
        metrics = [
            m.model_copy(update={"status": MetricStatus.NO_SIGNAL, "reasons": []}) for m in base.metrics
        ]
        return base.model_copy(update={"metrics": metrics, "insufficient_reasons": [], **changes})

    return analyze


def _evidence(id_, ts="2026-03-05T10:00:00Z"):
    return Evidence(id=id_, source_type="ticket", timestamp=ts)


def _fails(client, expected_fragment):
    load(client)
    r = run(client)
    assert r.status_code == 500
    body = ErrorResponse.model_validate(r.json())
    assert expected_fragment in " ".join(body.details)
    assert client.get("/api/investigations").json() == []  # nothing stored


def test_analysis_wrong_as_of_fails(make_client):
    c = make_client(analyze_fn=_analysis_with(as_of="2026-01-01T00:00:00Z"))
    _fails(c, "as_of differs")


def test_analysis_future_evidence_fails(make_client):
    c = make_client(analyze_fn=_analysis_with(evidence=[_evidence("t-1", "2026-07-01T00:00:00Z")]))
    _fails(c, "after as_of")


def test_analysis_unknown_evidence_fails(make_client):
    c = make_client(analyze_fn=_analysis_with(evidence=[_evidence("not-a-record")]))
    _fails(c, "not a record in the dataset")


def test_analysis_known_evidence_passes(make_client):
    inv = investigate(make_client(analyze_fn=_analysis_with(evidence=[_evidence("t-1")])))
    assert inv["analysis"]["evidence"][0]["id"] == "t-1"


def test_analysis_missing_metric_fails(make_client):
    def analyze(dataset, policy_id, as_of):
        base = _analysis_with()(dataset, policy_id, as_of)
        return base.model_copy(update={"metrics": base.metrics[:2]})

    _fails(make_client(analyze_fn=analyze), "each of the three metrics")


def test_unhandled_error_is_logged_with_request_id(make_client, caplog):
    def broken(dataset, policy_id, as_of):
        raise RuntimeError("kaboom")

    c = make_client(analyze_fn=broken)
    load(c)
    with caplog.at_level(logging.ERROR, logger="incento"):
        r = run(c)
    assert r.status_code == 500 and r.json()["code"] == "internal_error"
    assert any(r.json()["request_id"] in rec.getMessage() for rec in caplog.records)


# --- outcomes, seeding, reset ---


def test_retain_crash_and_timeout_keep_the_outcome(make_client, memory):
    c = make_client({"retain_timeout_seconds": 0.05})
    inv = investigate(c)
    path = f"/api/incidents/{inv['incident_id']}/outcomes"
    body = {
        "type": "decision",
        "run_id": inv["run_id"],
        "event_time": "2026-07-10T00:00:00Z",
        "idempotency_key": "outcome-crash-1",
    }

    def boom(outcome, scenario):
        raise RuntimeError("down")

    memory.retain_outcome = boom
    crashed = c.post(path, json=body).json()
    assert crashed["retention_status"] == "failed" and crashed["retention_error"] == "retention_error"

    def slow(outcome, scenario):
        time.sleep(0.5)

    memory.retain_outcome = slow
    out2 = c.post(path, json={**body, "idempotency_key": "outcome-crash-2"}).json()
    assert out2["retention_error"] == "retention_timeout"
    assert len(c.get(f"/api/incidents/{inv['incident_id']}").json()["outcomes"]) == 2


def test_seed_failure_is_reported_not_fatal(make_client, memory, fixtures_dir):
    data = tiny_dataset("seeded")
    data["history"] = [
        {
            "incident_id": "hist-1",
            "title": "Old incident",
            "occurred_at": "2025-01-01T00:00:00Z",
            "records": [
                {
                    "record_id": "rec-1",
                    "memory_type": "fact",
                    "event_time": "2025-01-01T00:00:00Z",
                    "summary": "x",
                }
            ],
        }
    ]
    (fixtures_dir / "seeded.json").write_text(json.dumps(data))

    def boom(history, scenario):
        raise RuntimeError("down")

    memory.seed_history = boom
    r = make_client().post("/api/demo/load", json={"scenario": "seeded"})
    assert r.status_code == 200
    assert r.json()["seed_status"] == "unavailable" and r.json()["seed_error"] == "seed_error"


def test_reset_with_failing_real_memory_leaves_state_alone(make_client, memory):
    memory.reset_demo_bank = lambda scenario: ResetResult(ok=False, error="bank_locked")
    c = make_client(stubbed=[])  # memory is "real", so a failed reset must not clear SQLite
    investigate(c)
    r = c.post("/api/demo/reset", json={"scenario": "tiny", "confirm": True})
    assert r.status_code == 502 and r.json()["code"] == "memory_unavailable"
    assert len(c.get("/api/investigations").json()) == 1


def test_reset_with_stub_memory_still_clears_sqlite(make_client, memory):
    memory.reset_demo_bank = lambda scenario: ResetResult(ok=False, error="memory_not_connected")
    c = make_client(stubbed=["reset_demo_bank"])
    investigate(c)
    r = c.post("/api/demo/reset", json={"scenario": "tiny", "confirm": True})
    assert r.status_code == 200 and r.json()["memory_reset"] is False
    assert c.get("/api/investigations").json() == []


def test_reset_rejects_unsafe_scenario_name(client):
    r = client.post("/api/demo/reset", json={"scenario": "../../x", "confirm": True})
    assert r.status_code == 422


def test_note_is_stripped_of_urls_and_markdown(client):
    inv = investigate(client)
    body = {
        "type": "decision",
        "run_id": inv["run_id"],
        "event_time": "2026-07-10T00:00:00Z",
        "note": "See [this](https://evil.example/x) and www.evil.example now\n`code`",
        "idempotency_key": "outcome-note-1",
    }
    note = client.post(f"/api/incidents/{inv['incident_id']}/outcomes", json=body).json()["note"]
    assert "evil" not in note and "[" not in note and "`" not in note and "\n" not in note
    assert note.startswith("See")


# --- fixtures ---


def test_non_synthetic_dataset_is_rejected(client, fixtures_dir):
    data = tiny_dataset("real")
    data["meta"]["synthetic"] = False
    (fixtures_dir / "real.json").write_text(json.dumps(data))
    r = client.post("/api/demo/load", json={"scenario": "real"})
    assert r.status_code == 422 and "synthetic" in r.json()["message"]


def test_duplicate_ids_and_scenario_mismatch_are_rejected(client, fixtures_dir):
    data = tiny_dataset("dupes")
    data["customers"].append(data["customers"][0])
    data["deals"].append(data["deals"][0])
    (fixtures_dir / "dupes.json").write_text(json.dumps(data))
    r = client.post("/api/demo/load", json={"scenario": "dupes"})
    assert r.status_code == 422
    assert "duplicate customer IDs" in r.json()["details"] and "duplicate deal IDs" in r.json()["details"]

    (fixtures_dir / "other.json").write_text(json.dumps(tiny_dataset("not-other")))
    assert client.post("/api/demo/load", json={"scenario": "other"}).status_code == 422


def test_changed_fixture_requires_reload(client, fixtures_dir):
    load(client)
    data = tiny_dataset()
    data["deals"][0]["discount"] = 0.3
    (fixtures_dir / "tiny.json").write_text(json.dumps(data))
    r = run(client)
    assert r.status_code == 409 and r.json()["code"] == "scenario_not_loaded"
    reload = load(client).json()
    assert reload["already_loaded"] is False
    assert run(client).status_code == 201


# --- concurrency and configuration ---


def test_parallel_same_key_creates_one_run(client):
    load(client)

    def post(_):
        return run(client)

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(post, range(8)))
    assert all(r.status_code in (200, 201) for r in responses)
    assert sum(r.status_code == 201 for r in responses) == 1
    assert len({r.json()["run_id"] for r in responses}) == 1
    assert len(client.get("/api/investigations").json()) == 1


def test_parallel_different_keys_all_succeed(client):
    load(client)

    def post(i):
        return run(client, idempotency_key=f"parallel-key-{i:03d}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(post, range(8)))
    assert all(r.status_code == 201 for r in responses)
    assert len({r.json()["run_id"] for r in responses}) == 8
    Investigation.model_validate(responses[0].json())


def test_relative_database_path_resolves_to_repo_root():
    assert Settings(database_path=".local/x.sqlite3").resolved_database_path == str(
        REPO_ROOT / ".local" / "x.sqlite3"
    )
    assert Settings(database_path=":memory:").resolved_database_path == ":memory:"
    assert Settings(database_path="/abs/x.sqlite3").resolved_database_path == "/abs/x.sqlite3"


def test_health_reports_stubs_and_never_live_memory(client):
    h = client.get("/api/health").json()
    assert h["memory_status"] != MemoryStatus.LIVE.value
    assert BODY["scenario"]


# --- a seeded record is shown as the dataset stores it ---


def test_recalled_seeded_record_is_shown_with_its_stored_text():
    from app.core.fixtures import load_dataset
    from app.core.guards import canonical_recalled

    ds, _ = load_dataset(str(REPO_ROOT / "data" / "scenarios"), "risk")
    stored = {r.record_id: r for inc in ds.history for r in inc.records}
    rephrased = RecalledMemory(
        id="HIST-RISK-RESULT",
        memory_type="fact",
        event_time="2026-01-01T00:00:00Z",
        incident_id="INC-RISK-PRIOR",
        summary="The abrupt suspension caused seller departures.",
    )
    outcome = _recalled()  # an outcome id is not a seeded record and stays as returned
    explanation = good_explain_for_risk().model_copy(update={"recalled": [rephrased, outcome]})
    fixed = canonical_recalled(explanation, ds).recalled
    assert fixed[0].summary == stored["HIST-RISK-RESULT"].summary
    assert fixed[0].memory_type == stored["HIST-RISK-RESULT"].memory_type
    assert fixed[0].event_time == stored["HIST-RISK-RESULT"].event_time
    assert fixed[1] == outcome


def good_explain_for_risk():
    from app.core.schemas import Explanation, ExplanationSource

    return Explanation(
        summary="s",
        hypothesis="h",
        recommendations=[],
        explanation_source=ExplanationSource.TEMPLATE,
        memory_status=MemoryStatus.LIVE,
    )
