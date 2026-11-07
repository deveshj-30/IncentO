"""Tests for P4's memory adapter, validation, and explanation service."""

import os
from datetime import UTC, datetime
from pathlib import Path

from app.core.schemas import (
    ActionType,
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
    SeedStatus,
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


def test_explain_memory_off(tmp_path: Path) -> None:
    store = tmp_path / "banks.json"
    service.set_adapter(HindsightAdapter(api_key="", store_path=store))
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


def test_unconfigured_key_reports_truthful_status(tmp_path: Path) -> None:
    store = tmp_path / "banks.json"
    # Ensure no simulation flag
    os.environ.pop("HINDSIGHT_SIMULATE", None)
    adapter = HindsightAdapter(api_key="", store_path=store)
    service.set_adapter(adapter)

    # Retain without key returns failed + memory_not_configured
    outcome = Outcome(
        outcome_id="out-unconf-1",
        type=OutcomeType.DECISION,
        incident_id="inc-1",
        run_id="run-1",
        event_time=datetime(2026, 1, 1, tzinfo=UTC),
        note="Decision note",
        idempotency_key="idemp-unconf",
        retention_status=RetentionStatus.PENDING,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    ret_res = service.retain_outcome(outcome, scenario="risk")
    assert ret_res.status == RetentionStatus.FAILED
    assert ret_res.error == "memory_not_configured"

    # Seed without key returns unavailable + memory_not_configured
    seed_res = service.seed_history([], scenario="risk")
    assert seed_res.status == SeedStatus.SKIPPED  # empty incidents skipped
    seed_res2 = service.seed_history(
        [
            HistoricalIncident(
                incident_id="inc-1",
                title="Past Inc",
                occurred_at=datetime(2025, 1, 1, tzinfo=UTC),
                records=[
                    HistoryRecord(
                        record_id="rec-1",
                        memory_type=RecalledMemoryType.FACT,
                        event_time=datetime(2025, 1, 1, tzinfo=UTC),
                        summary="Past fact",
                    )
                ],
            )
        ],
        scenario="risk",
    )
    assert seed_res2.status == SeedStatus.UNAVAILABLE
    assert seed_res2.error == "memory_not_configured"


def test_explain_memory_live_with_simulated_seed(tmp_path: Path) -> None:
    store = tmp_path / "banks.json"
    os.environ["HINDSIGHT_SIMULATE"] = "1"
    try:
        adapter = HindsightAdapter(api_key="", store_path=store)
        service.set_adapter(adapter)
        as_of = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)

        # Seed past incident from 2025 into tiny scenario
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
        assert seed_res.status == SeedStatus.SEEDED

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
    finally:
        os.environ.pop("HINDSIGHT_SIMULATE", None)


def test_chronology_enforcement_filters_future_memory(tmp_path: Path) -> None:
    store = tmp_path / "banks.json"
    os.environ["HINDSIGHT_SIMULATE"] = "1"
    try:
        adapter = HindsightAdapter(api_key="", store_path=store)
        service.set_adapter(adapter)
        as_of = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)

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
        assert all(m.id != "mem-future-1" for m in exp.recalled)
    finally:
        os.environ.pop("HINDSIGHT_SIMULATE", None)


def test_retain_outcome_and_recall_loop(tmp_path: Path) -> None:
    store = tmp_path / "banks.json"
    os.environ["HINDSIGHT_SIMULATE"] = "1"
    try:
        adapter = HindsightAdapter(api_key="", store_path=store)
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

        res = service.retain_outcome(outcome, scenario="tiny")
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
        assert "out-101" in recalled_ids
    finally:
        os.environ.pop("HINDSIGHT_SIMULATE", None)


def test_undated_result_dropped_by_adapter(tmp_path: Path) -> None:
    store = tmp_path / "banks.json"
    adapter = HindsightAdapter(api_key="", store_path=store)
    as_of = datetime(2026, 3, 1, tzinfo=UTC)

    # Item with no timestamp whatsoever
    undated_item = {"id": "item-1", "text": "Some undated text"}
    parsed = adapter._parse_cloud_result(undated_item, as_of)
    assert parsed is None

    # Item with valid timestamp
    dated_item = {"id": "item-2", "text": "Dated text", "timestamp": "2026-01-15T00:00:00Z"}
    parsed = adapter._parse_cloud_result(dated_item, as_of)
    assert parsed is not None
    assert parsed.id == "item-2"

    # Item with future timestamp relative to as_of
    future_item = {"id": "item-3", "text": "Future text", "timestamp": "2026-05-15T00:00:00Z"}
    parsed = adapter._parse_cloud_result(future_item, as_of)
    assert parsed is None

    # Untraceable internal Cloud observation with bare UUID is dropped
    uuid_item = {
        "id": "845c3be4-e36b-4e4b-972f-5ea86ba6d3e6",
        "text": "Internal Cloud synthesized observation",
        "timestamp": "2026-01-15T00:00:00Z",
    }
    parsed = adapter._parse_cloud_result(uuid_item, as_of)
    assert parsed is None


def test_cross_restart_persistence(tmp_path: Path) -> None:
    store = tmp_path / "banks.json"
    os.environ["HINDSIGHT_SIMULATE"] = "1"
    try:
        adapter1 = HindsightAdapter(api_key="", store_path=store)
        outcome = Outcome(
            outcome_id="out-persist-99",
            type=OutcomeType.DECISION,
            incident_id="inc-p-1",
            run_id="run-p-1",
            event_time=datetime(2026, 2, 1, tzinfo=UTC),
            note="Persist test",
            idempotency_key="idemp-persist",
            retention_status=RetentionStatus.PENDING,
            created_at=datetime(2026, 2, 1, tzinfo=UTC),
        )
        res = adapter1.retain_outcome("incento-demo-persist", outcome)
        assert res.status == RetentionStatus.RETAINED

        # Emulate server restart by instantiating new adapter pointing to the same store
        adapter2 = HindsightAdapter(api_key="", store_path=store)
        recalled = adapter2.recall("incento-demo-persist", "query", as_of=datetime(2026, 3, 1, tzinfo=UTC))
        assert len(recalled) == 1
        assert recalled[0].id == "out-persist-99"
    finally:
        os.environ.pop("HINDSIGHT_SIMULATE", None)


def test_reset_demo_bank(tmp_path: Path) -> None:
    store = tmp_path / "banks.json"
    adapter = HindsightAdapter(api_key="", store_path=store)
    service.set_adapter(adapter)
    bank_name = adapter.get_bank_name("tiny", is_demo=True)
    assert bank_name == "incento-demo-tiny"

    # Resetting a demo bank succeeds
    reset_res = service.reset_demo_bank("tiny")
    assert reset_res.ok is True


def test_recalled_empty_when_memory_status_unavailable(tmp_path: Path) -> None:
    """When memory is unavailable (no key and no simulation), recalled list is strictly empty."""
    store = tmp_path / "banks.json"
    os.environ.pop("HINDSIGHT_SIMULATE", None)
    adapter = HindsightAdapter(api_key="", store_path=store)
    service.set_adapter(adapter)
    as_of = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    analysis = _sample_analysis(as_of)
    ctx = ExplainContext(
        run_id="run-unavail",
        scenario="tiny",
        policy_id="pol-acq-bonus",
        as_of=as_of,
        memory_mode=MemoryMode.LIVE,
        incident_id="inc-1",
    )
    exp = service.explain(analysis, ctx)
    assert exp.memory_status == MemoryStatus.UNAVAILABLE
    assert exp.recalled == []


def test_store_path_resolves_to_repo_root() -> None:
    from app.memory.hindsight_adapter import LOCAL_STORE_PATH, REPO_ROOT

    assert LOCAL_STORE_PATH.is_absolute()
    assert str(LOCAL_STORE_PATH) == str(REPO_ROOT / ".local" / "hindsight_banks.json")


def test_rejected_hypothesis_never_influences_recommendation(tmp_path: Path) -> None:
    """A recalled rejected hypothesis or fact never flips advice or appears in history_influence."""
    store = tmp_path / "banks.json"
    os.environ["HINDSIGHT_SIMULATE"] = "1"
    try:
        adapter = HindsightAdapter(api_key="", store_path=store)
        service.set_adapter(adapter)
        as_of = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)

        # Seed only a rejected hypothesis and a generic fact
        incident_time = datetime(2025, 10, 15, 0, 0, 0, tzinfo=UTC)
        service.seed_history(
            [
                HistoricalIncident(
                    incident_id="inc-hist-rejected",
                    title="Prior Review",
                    occurred_at=incident_time,
                    records=[
                        HistoryRecord(
                            record_id="HIST-RISK-FACT",
                            memory_type=RecalledMemoryType.FACT,
                            event_time=incident_time,
                            summary="A prior review checked customer onboarding.",
                        ),
                        HistoryRecord(
                            record_id="HIST-RISK-REJECTED",
                            memory_type=RecalledMemoryType.REJECTED_HYPOTHESIS,
                            event_time=incident_time,
                            summary="A previous incentive explanation was rejected.",
                        ),
                    ],
                )
            ],
            scenario="tiny",
        )

        analysis = _sample_analysis(as_of)
        ctx = ExplainContext(
            run_id="run-rej-check",
            scenario="tiny",
            policy_id="pol-acq-bonus",
            as_of=as_of,
            memory_mode=MemoryMode.LIVE,
            incident_id="inc-1",
        )
        exp = service.explain(analysis, ctx)
        # Recalled list contains the items
        recalled_ids = [m.id for m in exp.recalled]
        assert "HIST-RISK-REJECTED" in recalled_ids

        # But recommendation is NOT flipped to pilot_guardrail and history_influence is empty!
        for rec in exp.recommendations:
            assert rec.action_type == ActionType.REVERT_CHANGE
            assert "HIST-RISK-REJECTED" not in rec.history_influence
            assert rec.history_influence == []
    finally:
        os.environ.pop("HINDSIGHT_SIMULATE", None)


def test_validate_structured_output_rules() -> None:
    from app.memory.validation import validate_structured_output

    token_dict = {"m:discount.gap": "+14.6%", "t:min_group_size": "30"}
    valid_eids = {"EVID-1", "EVID-2"}
    valid_hids = {"MEM-1"}

    # Valid output with metric token and known citations passes
    valid_data = {
        "summary": "Discount gap is {{m:discount.gap}} divergence.",
        "hypothesis": "Policy divergence is observable across cohorts.",
        "supporting_points": ["Observed cohort gap."],
        "conflicting_points": [],
        "alternatives": ["Macro market conditions."],
        "recommendations": [
            {
                "action_type": "pilot_guardrail",
                "action": "Pilot a threshold approval.",
                "rationale": "Observed gap warrants guardrail.",
                "success_metric": "Reduce gap below threshold",
                "guardrail": "Maintain SLA",
                "evidence_ids": ["EVID-1"],
                "history_influence": ["MEM-1"],
            }
        ],
    }
    ok, err = validate_structured_output(valid_data, token_dict, valid_eids, valid_hids)
    assert ok is True
    assert err is None

    # Raw digits in summary fails number rules
    bad_digits = dict(valid_data, summary="Discount gap is 14.6% divergence.")
    ok, err = validate_structured_output(bad_digits, token_dict, valid_eids, valid_hids)
    assert ok is False
    assert "contains_digits" in str(err)

    # Unknown evidence citation fails
    bad_citation = {
        **valid_data,
        "recommendations": [{**valid_data["recommendations"][0], "evidence_ids": ["UNKNOWN-999"]}],
    }
    ok, err = validate_structured_output(bad_citation, token_dict, valid_eids, valid_hids)
    assert ok is False
    assert "unknown_evidence_citation" in str(err)


def _recalled(record_id: str, kind: RecalledMemoryType, day: int):
    from app.core.schemas import RecalledMemory

    return RecalledMemory(
        id=record_id,
        memory_type=kind,
        event_time=datetime(2025, 9, day, 12, tzinfo=UTC),
        incident_id="INC-RISK-PRIOR",
        summary="Synthetic prior record.",
    )


def test_measured_result_is_cited_whatever_order_recall_returns() -> None:
    """The cited record depends on the records, not on the order Cloud returned them in."""
    import itertools

    from app.memory.prompts import build_template_explanation

    as_of = datetime(2026, 11, 1, tzinfo=UTC)
    analysis = _sample_analysis(as_of)
    records = [
        _recalled("HIST-RISK-FACT", RecalledMemoryType.FACT, 12),
        _recalled("HIST-RISK-REJECTED", RecalledMemoryType.REJECTED_HYPOTHESIS, 14),
        _recalled("HIST-RISK-DECISION", RecalledMemoryType.DECISION, 15),
        _recalled("HIST-RISK-RESULT", RecalledMemoryType.MEASURED_RESULT, 1),
    ]
    for order in itertools.permutations(records):
        recs = build_template_explanation(analysis, ["TICKET-001"], list(order))[5]
        assert recs[0].action_type == ActionType.PILOT_GUARDRAIL
        assert recs[0].history_influence == ["HIST-RISK-RESULT"]


def test_decision_alone_is_cited_when_no_result_recalled() -> None:
    from app.memory.prompts import build_template_explanation

    analysis = _sample_analysis(datetime(2026, 11, 1, tzinfo=UTC))
    recs = build_template_explanation(
        analysis, ["TICKET-001"], [_recalled("HIST-RISK-DECISION", RecalledMemoryType.DECISION, 15)]
    )[5]
    assert recs[0].history_influence == ["HIST-RISK-DECISION"]


def test_recall_returns_every_seeded_record(tmp_path: Path) -> None:
    """Recall must not drop seeded records because of a small limit (it used to cap at three)."""
    os.environ["HINDSIGHT_SIMULATE"] = "1"
    try:
        service.set_adapter(HindsightAdapter(api_key="", store_path=tmp_path / "banks.json"))
        kinds = [
            ("HIST-RISK-FACT", RecalledMemoryType.FACT),
            ("HIST-RISK-REJECTED", RecalledMemoryType.REJECTED_HYPOTHESIS),
            ("HIST-RISK-DECISION", RecalledMemoryType.DECISION),
            ("HIST-RISK-RESULT", RecalledMemoryType.MEASURED_RESULT),
        ]
        when = datetime(2025, 9, 12, tzinfo=UTC)
        service.seed_history(
            [
                HistoricalIncident(
                    incident_id="INC-RISK-PRIOR",
                    title="Prior acquisition review",
                    occurred_at=when,
                    records=[
                        HistoryRecord(record_id=i, memory_type=k, event_time=when, summary="Synthetic.")
                        for i, k in kinds
                    ],
                )
            ],
            scenario="tiny",
        )
        as_of = datetime(2026, 11, 1, tzinfo=UTC)
        ctx = ExplainContext(
            run_id="run-recall-all",
            scenario="tiny",
            policy_id="pol-acq-bonus",
            as_of=as_of,
            memory_mode=MemoryMode.LIVE,
            incident_id="inc-1",
        )
        exp = service.explain(_sample_analysis(as_of), ctx)
        assert {m.id for m in exp.recalled} == {i for i, _ in kinds}
        assert exp.recommendations[0].history_influence == ["HIST-RISK-RESULT"]
    finally:
        os.environ.pop("HINDSIGHT_SIMULATE", None)


def test_normalize_citations_repairs_misplaced_ids_and_drops_invented_ones() -> None:
    out = {
        "summary": "s",
        "recommendations": [
            {
                "action_type": "pilot_guardrail",
                "evidence_ids": ["HIST-RISK-RESULT", "TICKET-001", "TICKET-INVENTED"],
                "history_influence": ["Prior decision led to seller departures.", "HIST-RISK-GHOST"],
            },
            {"action_type": "no_action", "evidence_ids": ["NOPE"], "history_influence": []},
        ],
    }
    fixed = service.normalize_citations(
        out, {"TICKET-001", "TICKET-002"}, {"HIST-RISK-RESULT"}, ["TICKET-001", "TICKET-002"]
    )
    first, second = fixed["recommendations"]
    assert first["evidence_ids"] == ["TICKET-001"]
    assert first["history_influence"] == ["HIST-RISK-RESULT"]
    assert second["evidence_ids"] == ["TICKET-001", "TICKET-002"]  # nothing valid cited: leading evidence
    assert second["history_influence"] == []
    assert out["recommendations"][0]["evidence_ids"][0] == "HIST-RISK-RESULT"  # input not mutated


def test_causal_wording_is_rejected_but_causation_disclaimer_is_not() -> None:
    from app.memory.validation import validate_explanation_text

    for bad, word in (
        ("Previous abrupt suspensions caused seller departures.", "caused"),
        ("Discounting may lead to more complaints.", "lead to"),
        ("Churn rose due to the change.", "due to"),
        ("Pipeline disruption resulted in lost deals.", "resulted in"),
    ):
        assert validate_explanation_text(bad, {}) == (False, f"causal_claim:{word}"), bad
    ok = "The gap may be associated with discounting; this does not establish causation."
    assert validate_explanation_text(ok, {}) == (True, None)
    assert validate_explanation_text("Seller departures followed the suspension.", {}) == (True, None)


def test_configured_status_follows_key_and_simulation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HINDSIGHT_SIMULATE", raising=False)
    service.set_adapter(HindsightAdapter(api_key="", store_path=tmp_path / "b.json"))
    assert service.configured_status() == MemoryStatus.UNAVAILABLE
    monkeypatch.setenv("HINDSIGHT_SIMULATE", "1")
    assert service.configured_status() == MemoryStatus.FIXTURE
    monkeypatch.delenv("HINDSIGHT_SIMULATE")
    service.set_adapter(HindsightAdapter(api_key="test-key", store_path=tmp_path / "b.json"))
    assert service.configured_status() == MemoryStatus.LIVE


def test_unreachable_cloud_never_falls_back_to_the_local_store_as_live(tmp_path: Path, monkeypatch) -> None:
    """With a key set but Cloud failing, local simulation records must not appear as live memory."""
    import httpx

    monkeypatch.delenv("HINDSIGHT_SIMULATE", raising=False)
    store = tmp_path / "banks.json"
    when = datetime(2025, 9, 12, tzinfo=UTC)
    seed_adapter = HindsightAdapter(api_key="", store_path=store)
    monkeypatch.setenv("HINDSIGHT_SIMULATE", "1")
    service.set_adapter(seed_adapter)
    service.seed_history(
        [
            HistoricalIncident(
                incident_id="INC-RISK-PRIOR",
                title="Prior",
                occurred_at=when,
                records=[
                    HistoryRecord(
                        record_id="HIST-RISK-RESULT",
                        memory_type=RecalledMemoryType.MEASURED_RESULT,
                        event_time=when,
                        summary="Synthetic.",
                    )
                ],
            )
        ],
        scenario="tiny",
    )
    monkeypatch.delenv("HINDSIGHT_SIMULATE")

    def boom(*args, **kwargs):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(httpx.Client, "post", boom)
    live = HindsightAdapter(api_key="test-key", store_path=store)
    service.set_adapter(live)
    as_of = datetime(2026, 11, 1, tzinfo=UTC)
    assert live.recall("incento-demo-tiny", "q", as_of=as_of) == []
    ctx = ExplainContext(
        run_id="run-offline",
        scenario="tiny",
        policy_id="pol-acq-bonus",
        as_of=as_of,
        memory_mode=MemoryMode.LIVE,
        incident_id="inc-1",
    )
    exp = service.explain(_sample_analysis(as_of), ctx)
    assert exp.recalled == []
    assert exp.memory_status == MemoryStatus.UNAVAILABLE
