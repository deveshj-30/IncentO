import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import schemas
from app.core.config import Settings
from app.main import create_app

app = create_app(Settings(database_path=":memory:"))
EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples"

EXAMPLE_MODELS = {
    "investigation-request.json": schemas.InvestigationRequest,
    "investigation-response.json": schemas.Investigation,
    "error-response.json": schemas.ErrorResponse,
    "outcome-request.json": schemas.OutcomeRequest,
    "outcome-response.json": schemas.Outcome,
}


@pytest.mark.parametrize("name,model", EXAMPLE_MODELS.items())
def test_example_parses_into_model(name, model):
    model.model_validate(json.loads((EXAMPLES / name).read_text()))


def test_every_example_is_covered():
    assert {p.name for p in EXAMPLES.glob("*.json")} == set(EXAMPLE_MODELS)


def test_health():
    r = TestClient(app).get("/api/health")
    assert r.status_code == 200
    schemas.HealthResponse.model_validate(r.json())
    assert "x-request-id" in r.headers


def test_validation_error_uses_common_shape():
    r = TestClient(app).post("/api/investigations", json={})
    assert r.status_code == 422
    body = schemas.ErrorResponse.model_validate(r.json())
    assert body.code == schemas.ErrorCode.VALIDATION_ERROR


def test_unknown_investigation_is_404_error_shape():
    r = TestClient(app).get("/api/investigations/nope")
    assert r.status_code == 404
    assert schemas.ErrorResponse.model_validate(r.json()).code == schemas.ErrorCode.NOT_FOUND


def _example_investigation() -> schemas.Investigation:
    return schemas.Investigation.model_validate(
        json.loads((EXAMPLES / "investigation-response.json").read_text())
    )


def test_example_evidence_is_self_consistent():
    from app.core.guards import explanation_codes

    inv = _example_investigation()
    a = inv.analysis
    ids = [e.id for e in a.evidence]
    assert len(ids) == len(set(ids))
    cited = {i for m in a.metrics for i in m.evidence_ids} | {
        i for alt in a.alternatives for i in alt.evidence_ids
    }
    assert cited <= set(ids), f"cited but missing from analysis.evidence: {sorted(cited - set(ids))}"
    assert all(e.timestamp <= a.as_of for e in a.evidence)
    assert explanation_codes(inv.explanation, a, inv.memory_mode, a.as_of) == []


def test_example_metric_statuses_follow_the_decision_rule():
    a = _example_investigation().analysis
    t = a.thresholds
    for m in a.metrics:
        if m.status == schemas.MetricStatus.INSUFFICIENT_DATA:
            assert min(m.month_end_n, m.other_n) < t.min_group_size or m.gap is None
            continue
        assert m.gap is not None and m.gap_interval is not None and m.pre_policy_gap is not None
        big = m.gap >= t.gap_threshold
        flagged = big and m.gap_interval.lower > 0 and m.gap - m.pre_policy_gap >= t.baseline_margin
        expected = (
            schemas.MetricStatus.FLAGGED
            if flagged
            else schemas.MetricStatus.WATCH
            if big
            else schemas.MetricStatus.NO_SIGNAL
        )
        assert m.status == expected, f"{m.name}: example says {m.status}, rule gives {expected}"
