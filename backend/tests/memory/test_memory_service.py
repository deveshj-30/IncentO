"""Tests for P4's memory adapter, validation, and explanation service."""

from datetime import UTC, datetime

from app.core.schemas import (
    AnalysisResult,
    CohortCounts,
    Evidence,
    ExplainContext,
    ExplanationSource,
    HistoricalIncident,
    HistoryRecord,
    Interval,
    MemoryMode,
    MemoryStatus,
    MetricName,
    MetricResult,
    MetricStatus,
    Outcome,
    OutcomeType,
    RecalledMemoryType,
    RetentionStatus,
    SourceType,
    Theme,
)
from app.memory import service
from app.memory.hindsight_adapter import HindsightAdapter


def _sample_analysis(as_of: datetime, flagged: bool = True) -> AnalysisResult:
    evidence = [
        Evidence(
            id="TICKET-001",
            source_type=SourceType.TICKET,
            timestamp=as_of,
            theme=Theme.ONBOARDING_DIFFICULTY,
        ),
        Evidence(
            id="TICKET-002",
            source_type=SourceType.TICKET,
            timestamp=as_of,
            theme=Theme.MISSING_FEATURE,
        ),
    ]
    metrics = [
        MetricResult(
            name=MetricName.DISCOUNT,
            status=MetricStatus.FLAGGED if flagged else MetricStatus.NO_SIGNAL,
            month_end_value=0.28,
            other_value=0.15,
            gap=0.13,
            gap_interval=Interval(lower=0.08, upper=0.18, method="wilson"),
            pre_policy_gap=0.02,
            month_end_n=45,
            other_n=120,
            evidence_ids=["TICKET-001"],
        ),
        MetricResult(
            name=MetricName.COMPLAINT_30D,
            status=MetricStatus.FLAGGED if flagged else MetricStatus.NO_SIGNAL,
            month_end_value=0.22,
            other_value=0.09,
            gap=0.13,
            gap_interval=Interval(lower=0.05, upper=0.21, method="wilson"),
            pre_policy_gap=0.01,
            month_end_n=45,
            other_n=120,
            evidence_ids=["TICKET-002"],
        ),
        MetricResult(
            name=MetricName.CANCEL_30D,
            status=MetricStatus.NO_SIGNAL,
            month_end_value=0.04,
            other_value=0.03,
            gap=0.01,
            gap_interval=Interval(lower=-0.02, upper=0.04, method="wilson"),
            pre_policy_gap=0.0,
            month_end_n=45,
            other_n=120,
        ),
    ]
    return AnalysisResult(
        policy_id="pol-acq-bonus",
        policy_version="v1",
        scenario="tiny",
        as_of=as_of,
        comparison_id="month-end-v1",
        flagged=flagged,
        month_end=CohortCounts(label="Month-end deals", eligible=45, total=45),
        other=CohortCounts(label="Other deals", eligible=120, total=120),
        metrics=metrics,
        evidence=evidence,
    )


def test_explain_memory_off() -> None:
    service.set_adapter(HindsightAdapter())
    as_of = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    analysis = _sample_analysis(as_of)
    ctx = ExplainContext(
        run_id="run-1",
        scenario="tiny",
        policy_id="pol-acq-bonus",
        as_of=as_of,
        memory_mode=MemoryMode.OFF,
        incident_id="inc-1",
    )

    exp = service.explain(analysis, ctx)
    assert exp.explanation_source == ExplanationSource.TEMPLATE
    assert exp.memory_status == MemoryStatus.UNAVAILABLE
    assert exp.recalled == []
    for rec in exp.recommendations:
        assert rec.history_influence == []
        assert set(rec.evidence_ids) <= {"TICKET-001", "TICKET-002"}
    assert "Month-end deals" in exp.summary


def test_explain_memory_live_with_seed() -> None:
    adapter = HindsightAdapter()
    service.set_adapter(adapter)
    as_of = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)

    # Seed past incident from 2025
    incident_time = datetime(2025, 10, 15, 0, 0, 0, tzinfo=UTC)
    seed_res = service.seed_history(
        [
            HistoricalIncident(
                incident_id="inc-hist-2025-q3",
                title="Q3 2025 Flash Discount Spike",
                occurred_at=incident_time,
                records=[
                    HistoryRecord(
                        record_id="mem-hist-1",
                        memory_type=RecalledMemoryType.DECISION,
                        event_time=incident_time,
                        summary="Abrupt cancellation of bonus caused sales rep attrition.",
                    )
                ],
            )
        ],
        scenario="tiny",
    )
    assert seed_res.status.value == "seeded"

    analysis = _sample_analysis(as_of)
    ctx = ExplainContext(
        run_id="run-2",
        scenario="tiny",
        policy_id="pol-acq-bonus",
        as_of=as_of,
        memory_mode=MemoryMode.LIVE,
        incident_id="inc-1",
    )

    exp = service.explain(analysis, ctx)
    assert len(exp.recalled) > 0
    assert exp.recalled[0].id == "mem-hist-1"
    assert exp.recalled[0].event_time <= as_of
    assert exp.recommendations[0].history_influence == ["mem-hist-1"]


def test_chronology_enforcement_filters_future_memory() -> None:
    adapter = HindsightAdapter()
    service.set_adapter(adapter)
    as_of = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)

    # Seed memory in future relative to as_of
    future_time = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
    service.seed_history(
        [
            HistoricalIncident(
                incident_id="inc-future",
                title="Future Event",
                occurred_at=future_time,
                records=[
                    HistoryRecord(
                        record_id="mem-future-1",
                        memory_type=RecalledMemoryType.MEASURED_RESULT,
                        event_time=future_time,
                        summary="This happened in April 2026.",
                    )
                ],
            )
        ],
        scenario="tiny",
    )

    analysis = _sample_analysis(as_of)
    ctx = ExplainContext(
        run_id="run-3",
        scenario="tiny",
        policy_id="pol-acq-bonus",
        as_of=as_of,
        memory_mode=MemoryMode.LIVE,
        incident_id="inc-1",
    )

    exp = service.explain(analysis, ctx)
    # The future memory must NOT be recalled
    assert all(m.id != "mem-future-1" for m in exp.recalled)


def test_retain_outcome_and_recall_loop() -> None:
    adapter = HindsightAdapter()
    service.set_adapter(adapter)
    t1 = datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC)

    outcome = Outcome(
        outcome_id="out-101",
        type=OutcomeType.DECISION,
        incident_id="inc-tiny-1",
        run_id="run-1",
        event_time=t1,
        note="Approved a 1-quarter discount approval threshold pilot.",
        idempotency_key="idemp-1",
        retention_status=RetentionStatus.PENDING,
        created_at=t1,
    )

    res = service.retain_outcome(outcome)
    assert res.status == RetentionStatus.RETAINED

    # Subsequent investigation later in time should recall this retained decision
    t2 = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    analysis = _sample_analysis(t2)
    ctx = ExplainContext(
        run_id="run-4",
        scenario="tiny",
        policy_id="pol-acq-bonus",
        as_of=t2,
        memory_mode=MemoryMode.LIVE,
        incident_id="inc-tiny-1",
    )

    exp = service.explain(analysis, ctx)
    recalled_ids = [m.id for m in exp.recalled]
    assert "mem-out-101" in recalled_ids


def test_reset_demo_bank() -> None:
    adapter = HindsightAdapter()
    service.set_adapter(adapter)
    bank_name = adapter.get_bank_name("tiny", is_demo=True)
    assert bank_name == "incento-demo-tiny"

    # Resetting a demo bank succeeds
    reset_res = service.reset_demo_bank("tiny")
    assert reset_res.ok is True
