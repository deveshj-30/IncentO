import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import schemas
from app.main import app

EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples"

EXAMPLE_MODELS = {
    "investigation-request.json": schemas.InvestigationRequest,
    "investigation-response.json": schemas.Investigation,
    "error-response.json": schemas.ErrorResponse,
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
