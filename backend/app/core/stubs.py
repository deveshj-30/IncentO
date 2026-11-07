"""Clearly labeled stand-ins used until P3's analysis and P4's memory modules exist.

Stub output is never presented as real: the analysis reports ``insufficient_data`` with the reason
``stub_analyzer`` and the explanation is a template with memory status ``unavailable``.
"""

from datetime import datetime

from app.core.schemas import (
    ActionType,
    AnalysisResult,
    CohortCounts,
    Dataset,
    ExplainContext,
    Explanation,
    ExplanationSource,
    MemoryStatus,
    MetricName,
    MetricResult,
    MetricStatus,
    Recommendation,
    ResetResult,
    RetentionResult,
    RetentionStatus,
    SeedResult,
    SeedStatus,
)

STUB_REASON = "stub_analyzer"


def analyze(dataset: Dataset, policy_id: str, as_of: datetime) -> AnalysisResult:
    policy = next((p for p in dataset.policies if p.policy_id == policy_id), None)
    version = policy.version if policy else "unknown"
    in_scope = [d for d in dataset.deals if d.policy_id == policy_id and d.closed_at <= as_of]
    metrics = [
        MetricResult(
            name=name,
            status=MetricStatus.INSUFFICIENT_DATA,
            month_end_value=None,
            other_value=None,
            gap=None,
            gap_interval=None,
            pre_policy_gap=None,
            month_end_n=0,
            other_n=len(in_scope),
            reasons=[STUB_REASON],
        )
        for name in MetricName
    ]
    return AnalysisResult(
        policy_id=policy_id,
        policy_version=version,
        scenario=dataset.meta.scenario,
        as_of=as_of,
        comparison_id="month-end-v1",
        flagged=False,
        month_end=CohortCounts(label="Month-end deals", eligible=0, total=0),
        other=CohortCounts(label="Other deals", eligible=len(in_scope), total=len(in_scope)),
        metrics=metrics,
        insufficient_reasons=[STUB_REASON],
    )


def explain(analysis: AnalysisResult, context: ExplainContext) -> Explanation:
    text = "Stub explanation: the analysis and memory modules are not connected yet."
    return Explanation(
        summary=text,
        hypothesis="No hypothesis is available from stub modules.",
        recommendations=[
            Recommendation(
                action_type=ActionType.COLLECT_MORE_DATA,
                action="Connect the analysis module before drawing conclusions.",
                rationale="Stub output only.",
                success_metric="Real analysis available",
                guardrail="Do not act on stub output",
            )
        ],
        explanation_source=ExplanationSource.TEMPLATE,
        memory_status=MemoryStatus.UNAVAILABLE,
        validation_error_codes=["stub_explainer"],
    )


def retain_outcome(outcome, scenario: str) -> RetentionResult:
    return RetentionResult(status=RetentionStatus.FAILED, error="memory_not_connected")


def seed_history(incidents, scenario: str) -> SeedResult:
    return SeedResult(status=SeedStatus.UNAVAILABLE, error="memory_not_connected")


def reset_demo_bank(scenario: str) -> ResetResult:
    return ResetResult(ok=False, error="memory_not_connected")
