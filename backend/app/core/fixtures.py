"""Validate fixture batches and assemble datasets from loaded batches."""

import hashlib
import re
from pathlib import Path

from pydantic import ValidationError

from app.core.errors import ApiError
from app.core.schemas import Dataset, ErrorCode

_SCENARIO = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def validate_scenario_name(scenario: str) -> None:
    if not _SCENARIO.match(scenario):
        raise ApiError(422, ErrorCode.VALIDATION_ERROR, f"Invalid scenario name: {scenario!r}")


def load_dataset(fixtures_dir: str, scenario: str) -> tuple[Dataset, str]:
    """Return the validated dataset and the SHA-256 checksum of its file."""
    validate_scenario_name(scenario)
    path = Path(fixtures_dir) / f"{scenario}.json"
    if not path.is_file():
        raise ApiError(404, ErrorCode.NOT_FOUND, f"No fixture batch for scenario {scenario!r}")
    raw = path.read_bytes()
    try:
        dataset = Dataset.model_validate_json(raw)
    except ValidationError as exc:
        details = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:20]]
        raise ApiError(
            422, ErrorCode.VALIDATION_ERROR, f"Fixture batch {scenario!r} is invalid", details
        ) from exc
    problems = check_references(dataset)
    if problems:
        raise ApiError(
            422,
            ErrorCode.VALIDATION_ERROR,
            f"Fixture batch {scenario!r} has broken references",
            problems[:20],
        )
    if not dataset.meta.synthetic:
        raise ApiError(
            422,
            ErrorCode.VALIDATION_ERROR,
            "Only synthetic datasets may be loaded (meta.synthetic must be true)",
        )
    if dataset.meta.scenario != scenario:
        raise ApiError(422, ErrorCode.VALIDATION_ERROR, "meta.scenario does not match the file name")
    return dataset, hashlib.sha256(raw).hexdigest()


def check_references(ds: Dataset) -> list[str]:
    """Stable-ID referential integrity; never join on display names."""
    problems: list[str] = []
    policies = {(p.policy_id, p.version) for p in ds.policies}
    customers = {c.customer_id for c in ds.customers}
    deals = {d.deal_id: d for d in ds.deals}
    for d in ds.deals:
        if (d.policy_id, d.policy_version) not in policies:
            problems.append(f"deal {d.deal_id}: unknown policy {d.policy_id}/{d.policy_version}")
        if customers and d.customer_id not in customers:
            problems.append(f"deal {d.deal_id}: unknown customer {d.customer_id}")
    for kind, rows, key in (
        ("ticket", ds.tickets, "ticket_id"),
        ("cancellation", ds.cancellations, "cancellation_id"),
    ):
        for r in rows:
            deal = deals.get(r.deal_id)
            if deal is None:
                problems.append(f"{kind} {getattr(r, key)}: unknown deal {r.deal_id}")
            elif deal.customer_id != r.customer_id:
                problems.append(f"{kind} {getattr(r, key)}: customer does not match deal {r.deal_id}")
    for label, ids in (
        ("policy", [f"{p.policy_id}/{p.version}" for p in ds.policies]),
        ("customer", [c.customer_id for c in ds.customers]),
        ("history incident", [h.incident_id for h in ds.history]),
        ("history record", [r.record_id for h in ds.history for r in h.records]),
        ("deal", [d.deal_id for d in ds.deals]),
        ("ticket", [t.ticket_id for t in ds.tickets]),
        ("cancellation", [c.cancellation_id for c in ds.cancellations]),
    ):
        if len(ids) != len(set(ids)):
            problems.append(f"duplicate {label} IDs")
    return problems


def list_scenarios(fixtures_dir: str) -> list[str]:
    path = Path(fixtures_dir)
    return sorted(p.stem for p in path.glob("*.json")) if path.is_dir() else []
