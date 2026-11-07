"""Contract and decision-rule tests for deterministic cohort analysis."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.analysis.service import analyze
from app.core.guards import analysis_problems
from app.core.schemas import Dataset, MetricName, MetricStatus, Theme, Ticket

ROOT = Path(__file__).resolve().parents[3]
AS_OF = datetime(2026, 11, 1, tzinfo=UTC)


def scenario(name: str) -> Dataset:
    path = ROOT / "data" / "scenarios" / f"{name}.json"
    return Dataset.model_validate_json(path.read_bytes())


class AnalysisServiceTests(unittest.TestCase):
    def test_risk_metrics_and_evidence_match_fixture(self) -> None:
        dataset = scenario("risk")
        result = analyze(dataset, "POL-RISK-001", AS_OF)
        metrics = {metric.name: metric for metric in result.metrics}
        self.assertEqual(result.comparison_id, "month-end-v1")
        self.assertTrue(result.flagged)
        self.assertEqual(result.metrics_checked, 3)
        self.assertEqual((result.month_end.eligible, result.other.eligible), (120, 880))
        self.assertAlmostEqual(metrics[MetricName.DISCOUNT].gap, 0.15)
        self.assertAlmostEqual(metrics[MetricName.DISCOUNT].pre_policy_gap, 0.02)
        self.assertAlmostEqual(metrics[MetricName.COMPLAINT_30D].month_end_value, 0.30)
        self.assertAlmostEqual(metrics[MetricName.COMPLAINT_30D].other_value, 0.15)
        self.assertAlmostEqual(metrics[MetricName.CANCEL_30D].month_end_value, 0.25)
        self.assertAlmostEqual(metrics[MetricName.CANCEL_30D].other_value, 0.10)
        self.assertEqual({metric.status for metric in result.metrics}, {MetricStatus.FLAGGED})
        self.assertGreater(result.corroborating_customers, 1)
        self.assertEqual(analysis_problems(result, dataset, "POL-RISK-001", AS_OF), [])

    def test_outage_is_alternative_not_incentive_flag(self) -> None:
        dataset = scenario("outage")
        result = analyze(dataset, "POL-OUTAGE-001", AS_OF)
        metrics = {metric.name: metric for metric in result.metrics}
        self.assertFalse(result.flagged)
        self.assertTrue(all(metric.status == MetricStatus.NO_SIGNAL for metric in result.metrics))
        self.assertAlmostEqual(metrics[MetricName.COMPLAINT_30D].month_end_value, 0.30)
        self.assertAlmostEqual(metrics[MetricName.COMPLAINT_30D].other_value, 0.30)
        self.assertEqual(len(result.alternatives), 1)
        self.assertIn("Outage", result.alternatives[0].label)
        self.assertEqual(analysis_problems(result, dataset, "POL-OUTAGE-001", AS_OF), [])

    def test_sparse_groups_return_insufficient_data(self) -> None:
        dataset = scenario("sparse")
        result = analyze(dataset, "POL-SPARSE-001", AS_OF)
        self.assertFalse(result.flagged)
        self.assertEqual(result.month_end.eligible, 18)
        self.assertTrue(all(metric.status == MetricStatus.INSUFFICIENT_DATA for metric in result.metrics))
        self.assertEqual(len(result.insufficient_reasons), 3)
        self.assertEqual(analysis_problems(result, dataset, "POL-SPARSE-001", AS_OF), [])

    def test_immature_deals_have_distinct_rate_denominators(self) -> None:
        dataset = scenario("risk")
        earlier = datetime(2026, 9, 15, tzinfo=UTC)
        result = analyze(dataset, "POL-RISK-001", earlier)
        metrics = {metric.name: metric for metric in result.metrics}
        self.assertGreater(result.month_end.excluded_immature, 0)
        self.assertGreater(
            metrics[MetricName.DISCOUNT].month_end_n, metrics[MetricName.COMPLAINT_30D].month_end_n
        )
        self.assertEqual(metrics[MetricName.COMPLAINT_30D].month_end_n, result.month_end.eligible)
        self.assertTrue(all(item.timestamp <= earlier for item in result.evidence))
        self.assertEqual(analysis_problems(result, dataset, "POL-RISK-001", earlier), [])

    def test_no_post_policy_deals_returns_null_estimates(self) -> None:
        dataset = scenario("risk")
        early = datetime(2026, 2, 1, tzinfo=UTC)
        result = analyze(dataset, "POL-RISK-001", early)
        self.assertFalse(result.flagged)
        self.assertEqual((result.month_end.total, result.other.total), (0, 0))
        for metric in result.metrics:
            self.assertEqual(metric.status, MetricStatus.INSUFFICIENT_DATA)
            self.assertIsNone(metric.gap)
            self.assertIsNone(metric.gap_interval)
        self.assertEqual(analysis_problems(result, dataset, "POL-RISK-001", early), [])

    def test_out_of_scope_deal_cannot_change_comparison(self) -> None:
        dataset = scenario("risk")
        baseline = analyze(dataset, "POL-RISK-001", AS_OF)
        extra = dataset.deals[500].model_copy(
            update={"deal_id": "DEAL-OUT-OF-SCOPE", "segment": "enterprise", "discount": 1.0}
        )
        dataset.deals.append(extra)
        actual = analyze(dataset, "POL-RISK-001", AS_OF)
        self.assertEqual(actual.month_end, baseline.month_end)
        self.assertEqual(actual.other, baseline.other)
        self.assertEqual(actual.metrics, baseline.metrics)

    def test_seeded_history_does_not_change_analysis(self) -> None:
        dataset = scenario("risk")
        with_history = analyze(dataset, "POL-RISK-001", AS_OF)
        without_history = analyze(dataset.model_copy(update={"history": []}), "POL-RISK-001", AS_OF)
        self.assertEqual(with_history, without_history)

    def test_future_and_duplicate_tickets_do_not_change_rates(self) -> None:
        dataset = scenario("risk")
        baseline = analyze(dataset, "POL-RISK-001", AS_OF)
        existing = dataset.tickets[0]
        dataset.tickets.append(existing.model_copy())
        deal = next(deal for deal in dataset.deals if deal.deal_id == existing.deal_id)
        dataset.tickets.append(
            Ticket(
                ticket_id="TICKET-FUTURE-001",
                customer_id=existing.customer_id,
                deal_id=existing.deal_id,
                created_at=AS_OF + timedelta(days=1),
                theme=Theme.ONBOARDING_DIFFICULTY,
            )
        )
        dataset.tickets.append(
            Ticket(
                ticket_id="TICKET-DUPLICATE-CUSTOMER",
                customer_id=existing.customer_id,
                deal_id=deal.deal_id,
                created_at=existing.created_at + timedelta(hours=1),
                theme=Theme.ONBOARDING_DIFFICULTY,
            )
        )
        actual = analyze(dataset, "POL-RISK-001", AS_OF)
        self.assertEqual(
            [metric.month_end_value for metric in actual.metrics],
            [metric.month_end_value for metric in baseline.metrics],
        )
        self.assertEqual(
            [metric.other_value for metric in actual.metrics],
            [metric.other_value for metric in baseline.metrics],
        )
        self.assertNotIn("TICKET-FUTURE-001", {item.id for item in actual.evidence})

    def test_rejects_unknown_policy_and_naive_cutoff(self) -> None:
        dataset = scenario("risk")
        with self.assertRaisesRegex(ValueError, "Unknown policy_id"):
            analyze(dataset, "POL-MISSING", AS_OF)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            analyze(dataset, "POL-RISK-001", datetime(2026, 11, 1))


if __name__ == "__main__":
    unittest.main()
