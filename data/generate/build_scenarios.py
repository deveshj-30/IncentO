"""Build reproducible, synthetic scenario batches for contract review.

Run from the repository root with ``python data/generate/build_scenarios.py``.
The structure and measured outcomes are fixed by the scenario specification;
the seeded generator only varies harmless presentation details and close dates.
"""

from __future__ import annotations

import calendar
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONTHS = [(2026, month) for month in range(1, 10)]
EFFECTIVE_AT = "2026-04-01T00:00:00Z"
AS_OF = datetime(2026, 11, 1, tzinfo=UTC)
COMPANIES = (
    "Aster Ledger",
    "Blue Mango Systems",
    "Cedar Harbor",
    "Dawnfield Labs",
    "Eastbank Works",
    "Fable Commerce",
    "Grove Atlas",
    "Harborline Studio",
    "Indigo Circuit",
    "Juniper Thread",
    "Kitebridge Tools",
    "Lotus Vale",
)
INDUSTRIES = ("software", "logistics", "retail", "professional services")
REGIONS = ("Bengaluru", "Hyderabad", "Singapore", "London")


@dataclass(frozen=True)
class Group:
    deals: int
    complaints: int
    cancellations: int
    discount: float


@dataclass(frozen=True)
class Scenario:
    name: str
    seed: int
    pre_month_end: Group
    pre_other: Group
    post_month_end: Group
    post_other: Group
    complaint_theme: str


SCENARIOS = (
    Scenario(
        "risk",
        3107,
        Group(60, 9, 6, 0.12),
        Group(440, 66, 44, 0.10),
        Group(120, 36, 30, 0.25),
        Group(880, 132, 88, 0.10),
        "onboarding_difficulty",
    ),
    Scenario(
        "outage",
        4107,
        Group(60, 9, 6, 0.12),
        Group(440, 66, 44, 0.10),
        Group(120, 36, 12, 0.12),
        Group(880, 264, 88, 0.10),
        "outage",
    ),
    Scenario(
        "sparse",
        5107,
        Group(12, 2, 1, 0.12),
        Group(120, 18, 12, 0.10),
        Group(18, 6, 4, 0.25),
        Group(120, 18, 12, 0.10),
        "onboarding_difficulty",
    ),
)


def _stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _allocate(total: int, buckets: int) -> list[int]:
    return [total // buckets + (index < total % buckets) for index in range(buckets)]


def _close_days(year: int, month: int, month_end: bool) -> list[int]:
    last = calendar.monthrange(year, month)[1]
    days = range(last - 4, last + 1) if month_end else range(1, last - 4)
    return [day for day in days if datetime(year, month, day).weekday() < 5]


def build_scenario(spec: Scenario) -> dict:
    """Return one schema-shaped batch with deliberately exact group outcomes."""

    rng = random.Random(spec.seed)
    tag = spec.name.upper()
    policy_id = f"POL-{tag}-001"
    dataset = {
        "meta": {
            "scenario": spec.name,
            "synthetic": True,
            "generator_version": "1",
            "text_version": "structure-placeholder-1",
        },
        "policies": [
            {
                "policy_id": policy_id,
                "version": "v1",
                "name": f"{spec.name.title()} acquisition incentive",
                "effective_at": EFFECTIVE_AT,
                "segment": "mid-market",
                "channel": "direct",
                "description": "Synthetic acquisition incentive for comparison exercises.",
            }
        ],
        "customers": [],
        "deals": [],
        "tickets": [],
        "cancellations": [],
        "history": [
            {
                "incident_id": f"INC-{tag}-PRIOR",
                "title": "Prior acquisition review",
                "occurred_at": "2025-12-15T12:00:00Z",
                "records": [
                    {
                        "record_id": f"HIST-{tag}-FACT",
                        "memory_type": "fact",
                        "event_time": "2025-12-15T12:00:00Z",
                        "summary": "A prior review checked customer onboarding after an incentive change.",
                    },
                    {
                        "record_id": f"HIST-{tag}-REJECTED",
                        "memory_type": "rejected_hypothesis",
                        "event_time": "2025-12-16T12:00:00Z",
                        "summary": (
                            "A previous incentive explanation was rejected without "
                            "matched cohort evidence."
                        ),
                    },
                ],
            }
        ],
    }

    groups = (
        (MONTHS[:3], True, spec.pre_month_end),
        (MONTHS[:3], False, spec.pre_other),
        (MONTHS[3:], True, spec.post_month_end),
        (MONTHS[3:], False, spec.post_other),
    )
    for months, month_end, group in groups:
        month_counts = _allocate(group.deals, len(months))
        outage_window = spec.name == "outage" and months == MONTHS[3:]
        if outage_window:
            eligible_indices: list[int] = []
            offset = 0
            for (_, month), count in zip(months, month_counts, strict=True):
                if month in (7, 8):
                    eligible_indices.extend(range(offset + 1, offset + count + 1))
                offset += count
            complaint_indices = {
                index
                for position, index in enumerate(eligible_indices, start=1)
                if position * group.complaints // len(eligible_indices)
                > (position - 1) * group.complaints // len(eligible_indices)
            }
        else:
            complaint_indices = {
                index
                for index in range(1, group.deals + 1)
                if index * group.complaints // group.deals
                > (index - 1) * group.complaints // group.deals
            }
        index_in_group = 0
        for (year, month), count in zip(months, month_counts, strict=True):
            available_days = _close_days(year, month, month_end)
            for _ in range(count):
                index_in_group += 1
                sequence = len(dataset["deals"]) + 1
                deal_id = f"DEAL-{tag}-{sequence:04d}"
                customer_id = f"CUST-{tag}-{sequence:04d}"
                day = available_days[(index_in_group - 1) % len(available_days)]
                closed_at = datetime(year, month, day, 12, tzinfo=UTC)
                dataset["customers"].append(
                    {
                        "customer_id": customer_id,
                        "display_name": (
                            f"{COMPANIES[(sequence - 1) % len(COMPANIES)]} {sequence:04d}"
                        ),
                        "industry": INDUSTRIES[(sequence - 1) % len(INDUSTRIES)],
                        "region": REGIONS[(sequence - 1) % len(REGIONS)],
                    }
                )
                dataset["deals"].append(
                    {
                        "deal_id": deal_id,
                        "customer_id": customer_id,
                        "policy_id": policy_id,
                        "policy_version": "v1",
                        "segment": "mid-market",
                        "channel": "direct",
                        "closed_at": _stamp(closed_at),
                        "revenue": {
                            "amount_minor": rng.randint(45, 180) * 10000,
                            "currency": "USD",
                        },
                        "discount": group.discount,
                    }
                )
                has_complaint = index_in_group in complaint_indices
                has_cancellation = (
                    index_in_group * group.cancellations // group.deals
                ) > ((index_in_group - 1) * group.cancellations // group.deals)
                if has_complaint:
                    ticket_at = closed_at + timedelta(days=3 + (index_in_group % 23))
                    theme = (
                        spec.complaint_theme
                        if year == 2026 and month >= 4
                        else "onboarding_difficulty"
                    )
                    dataset["tickets"].append(
                        {
                            "ticket_id": f"TICKET-{tag}-{sequence:04d}",
                            "customer_id": customer_id,
                            "deal_id": deal_id,
                            "created_at": _stamp(ticket_at),
                            "theme": theme,
                            "excerpt": "Synthetic customer reported an onboarding concern.",
                        }
                    )
                if has_cancellation:
                    cancelled_at = closed_at + timedelta(
                        days=20 + (index_in_group % 10)
                    )
                    dataset["cancellations"].append(
                        {
                            "cancellation_id": f"CANCEL-{tag}-{sequence:04d}",
                            "customer_id": customer_id,
                            "deal_id": deal_id,
                            "cancelled_at": _stamp(cancelled_at),
                            "theme": (
                                "outage"
                                if spec.name == "outage" and month >= 4
                                else "onboarding_difficulty"
                            ),
                            "excerpt": "Synthetic customer ended the subscription.",
                        }
                    )

    return dataset


def main() -> None:
    target = ROOT / "scenarios"
    target.mkdir(parents=True, exist_ok=True)
    for spec in SCENARIOS:
        output = target / f"{spec.name}.json"
        dataset = build_scenario(spec)
        output.write_text(
            json.dumps(dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"{output}: {len(dataset['deals'])} deals")


if __name__ == "__main__":
    main()
