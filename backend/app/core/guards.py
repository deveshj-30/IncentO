"""Boundary checks on module output. P3 and P4 own their logic; P2 refuses output that breaks the contract.

Analysis violations are bugs and fail the request loudly. Explanation violations degrade to a labeled
fallback so the analytical result is still returned.
"""

from datetime import datetime

from app.core.errors import ApiError
from app.core.schemas import (
    AnalysisResult,
    Dataset,
    ErrorCode,
    Explanation,
    ExplanationSource,
    MemoryMode,
    MemoryStatus,
    MetricName,
)


def dataset_record_ids(ds: Dataset) -> set[str]:
    ids = {d.deal_id for d in ds.deals}
    ids |= {t.ticket_id for t in ds.tickets}
    ids |= {c.cancellation_id for c in ds.cancellations}
    ids |= {h.incident_id for h in ds.history}
    return ids


def analysis_problems(analysis: AnalysisResult, ds: Dataset, policy_id: str, as_of: datetime) -> list[str]:
    problems: list[str] = []
    if analysis.policy_id != policy_id:
        problems.append("analysis.policy_id differs from the request")
    if analysis.as_of != as_of:
        problems.append("analysis.as_of differs from the request")
    if analysis.scenario != ds.meta.scenario:
        problems.append("analysis.scenario differs from the dataset")
    names = [m.name for m in analysis.metrics]
    if sorted(names) != sorted(MetricName):
        problems.append("analysis.metrics must contain each of the three metrics exactly once")
    known = dataset_record_ids(ds)
    seen: set[str] = set()
    for e in analysis.evidence:
        if e.id in seen:
            problems.append(f"duplicate evidence id {e.id}")
        seen.add(e.id)
        if e.id not in known:
            problems.append(f"evidence {e.id} is not a record in the dataset")
        if e.timestamp > as_of:
            problems.append(f"evidence {e.id} is after as_of")
    cited = {i for m in analysis.metrics for i in m.evidence_ids} | {
        i for a in analysis.alternatives for i in a.evidence_ids
    }
    for missing in sorted(cited - seen):
        problems.append(f"cited evidence {missing} is not in analysis.evidence")
    return problems[:20]


def require_valid_analysis(analysis: AnalysisResult, ds: Dataset, policy_id: str, as_of: datetime) -> None:
    problems = analysis_problems(analysis, ds, policy_id, as_of)
    if problems:
        raise ApiError(500, ErrorCode.INTERNAL_ERROR, "Analysis output violates the contract", problems)


def explanation_codes(
    explanation: Explanation, analysis: AnalysisResult, mode: MemoryMode, as_of: datetime
) -> list[str]:
    """Non-secret error codes; empty when the explanation respects the contract."""
    codes: list[str] = []
    evidence_ids = {e.id for e in analysis.evidence}
    recalled_ids = {r.id for r in explanation.recalled}
    for rec in explanation.recommendations:
        if not set(rec.evidence_ids) <= evidence_ids:
            codes.append("unknown_evidence_citation")
        if not set(rec.history_influence) <= recalled_ids:
            codes.append("unknown_memory_citation")
    if any(r.event_time > as_of for r in explanation.recalled):
        codes.append("future_recalled_memory")
    if mode == MemoryMode.OFF and (
        explanation.recalled or any(r.history_influence for r in explanation.recommendations)
    ):
        codes.append("memory_used_while_off")
    return sorted(set(codes))


def fallback_explanation(codes: list[str]) -> Explanation:
    """Last-resort explanation when a module fails or breaks the contract. Never presented as live."""
    return Explanation(
        summary=(
            "The explanation service did not return a usable result. "
            "The calculated metrics are shown unchanged."
        ),
        hypothesis="No hypothesis is available.",
        recommendations=[],
        explanation_source=ExplanationSource.TEMPLATE,
        memory_status=MemoryStatus.UNAVAILABLE,
        validation_error_codes=codes,
    )
