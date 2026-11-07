import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import modules, stubs
from app.core.config import Settings
from app.core.schemas import (
    MetricStatus,
    ResetResult,
    RetentionResult,
    RetentionStatus,
    SeedResult,
    SeedStatus,
)
from app.main import create_app


def tiny_dataset(scenario: str = "tiny") -> dict:
    return {
        "meta": {
            "scenario": scenario,
            "synthetic": True,
            "generator_version": "test",
            "text_version": "test",
        },
        "policies": [
            {
                "policy_id": "pol-acq-bonus",
                "version": "v1",
                "name": "Acquisition bonus",
                "effective_at": "2026-01-01T00:00:00Z",
                "segment": "smb",
                "channel": "direct",
            }
        ],
        "customers": [
            {"customer_id": "cust-1", "display_name": "Acme Test", "industry": "retail", "region": "IN"}
        ],
        "deals": [
            {
                "deal_id": "deal-1",
                "customer_id": "cust-1",
                "policy_id": "pol-acq-bonus",
                "policy_version": "v1",
                "segment": "smb",
                "channel": "direct",
                "closed_at": "2026-02-28T10:00:00Z",
                "revenue": {"amount_minor": 120000, "currency": "USD"},
                "discount": 0.25,
            }
        ],
        "tickets": [
            {
                "ticket_id": "t-1",
                "customer_id": "cust-1",
                "deal_id": "deal-1",
                "created_at": "2026-03-05T10:00:00Z",
                "theme": "onboarding_difficulty",
            }
        ],
        "cancellations": [],
        "history": [],
    }


class FakeMemory:
    """Test double standing in for P4's module; never presented as live Hindsight."""

    def __init__(self):
        self.retained: list[str] = []
        self.retain_scenarios: list[str] = []
        self.seed_scenarios: list[str] = []
        self.status = RetentionStatus.RETAINED

    def retain_outcome(self, outcome, scenario):
        if self.status == RetentionStatus.RETAINED:
            self.retained.append(outcome.outcome_id)
            self.retain_scenarios.append(scenario)
        return RetentionResult(
            status=self.status, error=None if self.status != RetentionStatus.FAILED else "boom"
        )

    def seed_history(self, incidents, scenario):
        self.seed_scenarios.append(scenario)
        return SeedResult(status=SeedStatus.SEEDED)

    def reset_demo_bank(self, scenario):
        return ResetResult(ok=True)


def make_modules(
    memory: FakeMemory, *, flagged_incident: bool = True, explain=None, analyze_fn=None, stubbed=None
) -> modules.Modules:
    def analyze(dataset, policy_id, as_of):
        result = stubs.analyze(dataset, policy_id, as_of)
        if flagged_incident:
            # A real-looking, non-insufficient result so incidents are created.
            metrics = [
                m.model_copy(update={"status": MetricStatus.NO_SIGNAL, "reasons": []}) for m in result.metrics
            ]
            result = result.model_copy(update={"metrics": metrics, "insufficient_reasons": []})
        return result

    return modules.Modules(
        analyze=analyze_fn or analyze,
        explain=explain or stubs.explain,
        # Looked up at call time so tests can swap behavior after the client is built.
        retain_outcome=lambda outcome, scenario: memory.retain_outcome(outcome, scenario),
        seed_history=lambda incidents, scenario: memory.seed_history(incidents, scenario),
        reset_demo_bank=lambda scenario: memory.reset_demo_bank(scenario),
        stubbed=["explain"] if stubbed is None else stubbed,
    )


@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    d = tmp_path / "scenarios"
    d.mkdir()
    (d / "tiny.json").write_text(json.dumps(tiny_dataset()))
    return d


@pytest.fixture
def memory() -> FakeMemory:
    return FakeMemory()


@pytest.fixture
def make_client(fixtures_dir, memory):
    """Build a client with module overrides and settings overrides."""

    def build(settings_overrides=None, **module_kwargs):
        settings = Settings(
            database_path=":memory:",
            fixtures_dir=str(fixtures_dir),
            demo_reset_enabled=True,
            **(settings_overrides or {}),
        )
        return TestClient(
            create_app(settings, make_modules(memory, **module_kwargs)), raise_server_exceptions=False
        )

    return build


@pytest.fixture
def client(make_client):
    return make_client()
