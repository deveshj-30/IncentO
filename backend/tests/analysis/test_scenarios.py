"""Contract-independent checks for P3's draft synthetic batches."""

from __future__ import annotations

import calendar
import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[3]
GENERATOR = ROOT / "data" / "generate" / "build_scenarios.py"
SPEC = importlib.util.spec_from_file_location("build_scenarios", GENERATOR)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ScenarioDraftTests(TestCase):
    def test_committed_batches_match_deterministic_generator(self) -> None:
        for spec in MODULE.SCENARIOS:
            with self.subTest(scenario=spec.name):
                path = ROOT / "data" / "scenarios" / f"{spec.name}.json"
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")), MODULE.build_scenario(spec))

    def test_group_counts_and_source_links(self) -> None:
        for spec in MODULE.SCENARIOS:
            with self.subTest(scenario=spec.name):
                batch = MODULE.build_scenario(spec)
                deals = {deal["deal_id"]: deal for deal in batch["deals"]}
                customers = {customer["customer_id"] for customer in batch["customers"]}
                self.assertEqual(len(deals), len(batch["deals"]))
                self.assertEqual(len(customers), len(batch["customers"]))
                self.assertEqual(len(deals), len(customers))
                self.assertEqual(batch["meta"]["scenario"], spec.name)
                self.assertTrue(batch["meta"]["synthetic"])

                for months, is_month_end, group in (
                    (range(1, 4), True, spec.pre_month_end),
                    (range(1, 4), False, spec.pre_other),
                    (range(4, 10), True, spec.post_month_end),
                    (range(4, 10), False, spec.post_other),
                ):
                    members = [
                        deal
                        for deal in deals.values()
                        if datetime.fromisoformat(deal["closed_at"].replace("Z", "+00:00")).month in months
                        and self._is_month_end(deal["closed_at"]) == is_month_end
                    ]
                    member_ids = {deal["deal_id"] for deal in members}
                    self.assertEqual(len(members), group.deals)
                    self.assertEqual({deal["discount"] for deal in members}, {group.discount})
                    complaints = sum(ticket["deal_id"] in member_ids for ticket in batch["tickets"])
                    self.assertEqual(complaints, group.complaints)
                    self.assertEqual(
                        sum(cancel["deal_id"] in member_ids for cancel in batch["cancellations"]),
                        group.cancellations,
                    )

                for collection, id_field, time_field in (
                    (batch["tickets"], "ticket_id", "created_at"),
                    (batch["cancellations"], "cancellation_id", "cancelled_at"),
                ):
                    self.assertEqual(len({item[id_field] for item in collection}), len(collection))
                    for item in collection:
                        deal = deals[item["deal_id"]]
                        self.assertEqual(item["customer_id"], deal["customer_id"])
                        close = datetime.fromisoformat(deal["closed_at"].replace("Z", "+00:00"))
                        event = datetime.fromisoformat(item[time_field].replace("Z", "+00:00"))
                        self.assertLessEqual(close, event)
                        self.assertLessEqual(event, close + timedelta(days=30))
                        self.assertLessEqual(event, MODULE.AS_OF)
                for deal in deals.values():
                    self.assertIn(deal["customer_id"], customers)
                    close = datetime.fromisoformat(deal["closed_at"].replace("Z", "+00:00"))
                    self.assertLessEqual(close + timedelta(days=30), MODULE.AS_OF)

                if spec.name == "outage":
                    outage_tickets = [ticket for ticket in batch["tickets"] if ticket["theme"] == "outage"]
                    self.assertEqual(len(outage_tickets), 300)
                    self.assertTrue(
                        all(
                            datetime.fromisoformat(
                                deals[ticket["deal_id"]]["closed_at"].replace("Z", "+00:00")
                            ).month
                            in (7, 8)
                            for ticket in outage_tickets
                        )
                    )

                if spec.name == "risk":
                    incident = batch["history"][0]
                    records = {record["record_id"]: record for record in incident["records"]}
                    self.assertEqual(records["HIST-RISK-DECISION"]["memory_type"], "decision")
                    self.assertEqual(records["HIST-RISK-RESULT"]["memory_type"], "measured_result")
                    self.assertLess(
                        records["HIST-RISK-DECISION"]["event_time"],
                        records["HIST-RISK-RESULT"]["event_time"],
                    )
                    self.assertLess(incident["occurred_at"], records["HIST-RISK-DECISION"]["event_time"])
                    self.assertLess(records["HIST-RISK-RESULT"]["event_time"], MODULE.EFFECTIVE_AT)

    @staticmethod
    def _is_month_end(timestamp: str) -> bool:
        value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return value.day > calendar.monthrange(value.year, value.month)[1] - 5
