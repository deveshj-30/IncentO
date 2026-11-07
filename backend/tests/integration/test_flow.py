import json

from app.core.schemas import (
    DemoLoadResponse,
    ErrorCode,
    ErrorResponse,
    Incident,
    Investigation,
    Outcome,
    RetentionStatus,
)

BODY = {
    "policy_id": "pol-acq-bonus",
    "scenario": "tiny",
    "as_of": "2026-06-30T23:59:59Z",
    "memory_mode": "live",
    "idempotency_key": "run-key-0001",
}


def load(client, scenario="tiny"):
    return client.post("/api/demo/load", json={"scenario": scenario})


def run(client, **over):
    return client.post("/api/investigations", json={**BODY, **over})


def error_code(response) -> ErrorCode:
    return ErrorResponse.model_validate(response.json()).code


def test_load_is_idempotent_by_checksum(client):
    first = DemoLoadResponse.model_validate(load(client).json())
    second = DemoLoadResponse.model_validate(load(client).json())
    assert not first.already_loaded and second.already_loaded
    assert first.checksum == second.checksum and first.synthetic


def test_load_rejects_bad_names_and_unknown(client):
    assert load(client, "../etc/passwd").status_code == 422
    assert load(client, "missing").status_code == 404


def test_load_rejects_broken_references(client, fixtures_dir):
    from tests.conftest import tiny_dataset

    bad = tiny_dataset("bad")
    bad["tickets"][0]["deal_id"] = "nope"
    (fixtures_dir / "bad.json").write_text(json.dumps(bad))
    r = load(client, "bad")
    assert r.status_code == 422 and "unknown deal" in " ".join(r.json()["details"])


def test_policies_listed(client):
    r = client.get("/api/policies")
    assert [p["policy_id"] for p in r.json()] == ["pol-acq-bonus"]


def test_investigation_requires_loaded_scenario(client):
    r = run(client)
    assert r.status_code == 409 and error_code(r) == ErrorCode.SCENARIO_NOT_LOADED


def test_investigation_flow_idempotency_and_digest(client):
    load(client)
    first = run(client)
    assert first.status_code == 201
    inv = Investigation.model_validate(first.json())
    assert inv.incident_id == "inc-pol-acq-bonus-month-end-v1"

    again = run(client)
    assert again.status_code == 200 and again.json()["run_id"] == inv.run_id
    assert client.get("/api/investigations").json().__len__() == 1

    conflict = run(client, memory_mode="off")
    assert conflict.status_code == 409 and error_code(conflict) == ErrorCode.IDEMPOTENCY_CONFLICT

    off = Investigation.model_validate(run(client, memory_mode="off", idempotency_key="run-key-0002").json())
    assert off.analysis_digest == inv.analysis_digest  # same numbers in both modes
    assert client.get(f"/api/investigations/{inv.run_id}").status_code == 200
    assert client.get("/api/investigations/missing").status_code == 404


def test_unknown_policy(client):
    load(client)
    assert run(client, policy_id="nope").status_code == 404


def test_outcome_flow_idempotent_and_as_of_guard(client, memory):
    load(client)
    inv = Investigation.model_validate(run(client).json())
    path = f"/api/incidents/{inv.incident_id}/outcomes"
    body = {
        "type": "decision",
        "run_id": inv.run_id,
        "event_time": "2026-07-10T00:00:00Z",
        "note": "Approved <b>pilot</b>\x00",
        "idempotency_key": "outcome-key-1",
    }
    first = client.post(path, json=body)
    assert first.status_code == 201
    outcome = Outcome.model_validate(first.json())
    assert outcome.retention_status == RetentionStatus.RETAINED and "<" not in outcome.note

    again = client.post(path, json=body)
    assert again.status_code == 200 and again.json()["outcome_id"] == outcome.outcome_id
    assert memory.retained == [outcome.outcome_id]  # no duplicate retention

    changed = client.post(path, json={**body, "note": "different"})
    assert changed.status_code == 409 and error_code(changed) == ErrorCode.IDEMPOTENCY_CONFLICT

    incident = Incident.model_validate(client.get(f"/api/incidents/{inv.incident_id}").json())
    assert len(incident.outcomes) == 1 and incident.run_ids == [inv.run_id]
    assert client.get("/api/incidents").json()[0]["outcome_count"] == 1

    early = run(client, as_of="2026-07-01T00:00:00Z", idempotency_key="run-key-0003")
    assert early.status_code == 409 and error_code(early) == ErrorCode.AS_OF_BEFORE_MEMORY
    off = run(client, as_of="2026-07-01T00:00:00Z", memory_mode="off", idempotency_key="run-key-0004")
    assert off.status_code == 201


def test_outcome_validation(client):
    load(client)
    inv = Investigation.model_validate(run(client).json())
    body = {
        "type": "decision",
        "run_id": "other-run",
        "event_time": "2026-07-10T00:00:00Z",
        "idempotency_key": "outcome-key-2",
    }
    assert client.post(f"/api/incidents/{inv.incident_id}/outcomes", json=body).status_code == 422
    assert client.post("/api/incidents/nope/outcomes", json={**body, "run_id": inv.run_id}).status_code == 404
    long_note = {**body, "run_id": inv.run_id, "note": "x" * 281}
    assert client.post(f"/api/incidents/{inv.incident_id}/outcomes", json=long_note).status_code == 422


def test_pending_retention_blocks_live_run_then_retry(client, memory):
    load(client)
    inv = Investigation.model_validate(run(client).json())
    memory.status = RetentionStatus.PENDING
    body = {
        "type": "measured_result",
        "run_id": inv.run_id,
        "event_time": "2026-07-10T00:00:00Z",
        "idempotency_key": "outcome-key-3",
    }
    out = Outcome.model_validate(client.post(f"/api/incidents/{inv.incident_id}/outcomes", json=body).json())
    assert out.retention_status == RetentionStatus.PENDING
    blocked = run(client, as_of="2026-08-01T00:00:00Z", idempotency_key="run-key-0005")
    assert blocked.status_code == 409 and error_code(blocked) == ErrorCode.RETENTION_PENDING

    memory.status = RetentionStatus.RETAINED
    retry = client.post(f"/api/outcomes/{out.outcome_id}/retention")
    assert retry.json()["retention_status"] == "retained"
    assert client.post(f"/api/outcomes/{out.outcome_id}/retention").json()["retention_status"] == "retained"
    assert memory.retained == [out.outcome_id]
    assert run(client, as_of="2026-08-01T00:00:00Z", idempotency_key="run-key-0005").status_code == 201
    assert client.post("/api/outcomes/missing/retention").status_code == 404


def test_failed_retention_is_saved_and_reported(client, memory):
    load(client)
    inv = Investigation.model_validate(run(client).json())
    memory.status = RetentionStatus.FAILED
    body = {
        "type": "decision",
        "run_id": inv.run_id,
        "event_time": "2026-07-10T00:00:00Z",
        "idempotency_key": "outcome-key-4",
    }
    out = client.post(f"/api/incidents/{inv.incident_id}/outcomes", json=body).json()
    assert out["retention_status"] == "failed" and out["retention_error"] == "boom"
    assert len(client.get(f"/api/incidents/{inv.incident_id}").json()["outcomes"]) == 1


def test_demo_reset_clears_and_is_guarded(client, fixtures_dir, memory):
    load(client)
    run(client)
    r = client.post("/api/demo/reset", json={"scenario": "tiny", "confirm": True})
    assert r.status_code == 200 and r.json()["cleared_runs"] == 1 and r.json()["memory_reset"]
    assert client.get("/api/investigations").json() == []
    assert client.post("/api/demo/reset", json={"scenario": "tiny", "confirm": False}).status_code == 422


def test_demo_reset_disabled_by_default(fixtures_dir):
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    c = TestClient(create_app(Settings(database_path=":memory:", fixtures_dir=str(fixtures_dir))))
    r = c.post("/api/demo/reset", json={"scenario": "tiny", "confirm": True})
    assert r.status_code == 403 and r.json()["code"] == "forbidden"


def test_stub_modules_are_honest(fixtures_dir):
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    c = TestClient(create_app(Settings(database_path=":memory:", fixtures_dir=str(fixtures_dir))))
    health = c.get("/api/health").json()
    # analyze is now a real module (P3), so stubbed_modules should be empty
    assert "analyze" not in health["stubbed_modules"]


def test_scenario_is_passed_to_seed_and_retain(make_client, memory, fixtures_dir):
    import json

    from tests.conftest import tiny_dataset

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
    c = make_client()
    c.post("/api/demo/load", json={"scenario": "seeded"})
    assert memory.seed_scenarios == ["seeded"]

    inv = Investigation.model_validate(
        c.post(
            "/api/investigations", json={**BODY, "scenario": "seeded", "idempotency_key": "scen-key-0001"}
        ).json()
    )
    body = {
        "type": "decision",
        "run_id": inv.run_id,
        "event_time": "2026-07-10T00:00:00Z",
        "idempotency_key": "scen-out-0001",
    }
    out = c.post(f"/api/incidents/{inv.incident_id}/outcomes", json=body).json()
    assert memory.retain_scenarios == ["seeded"]

    memory.status = RetentionStatus.FAILED
    failed = c.post(
        f"/api/incidents/{inv.incident_id}/outcomes", json={**body, "idempotency_key": "scen-out-0002"}
    ).json()
    memory.status = RetentionStatus.RETAINED
    c.post(f"/api/outcomes/{failed['outcome_id']}/retention")
    assert memory.retain_scenarios == ["seeded", "seeded"]  # the retry also passes the incident's scenario
    assert out["retention_status"] == "retained"
