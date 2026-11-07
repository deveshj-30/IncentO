"""Public memory module entry points called by the core orchestrator."""

import logging

from app.core.schemas import (
    AnalysisResult,
    ExplainContext,
    Explanation,
    ExplanationSource,
    HistoricalIncident,
    MemoryMode,
    MemoryStatus,
    Outcome,
    ResetResult,
    RetentionResult,
    SeedResult,
)
from app.memory.hindsight_adapter import HindsightAdapter
from app.memory.prompts import build_template_explanation
from app.memory.validation import (
    build_token_dict,
    filter_memories_by_as_of,
    resolve_tokens,
    sanitize_recommendations,
)

log = logging.getLogger(__name__)

# Module-level default adapter instance
_adapter = HindsightAdapter()


def get_adapter() -> HindsightAdapter:
    return _adapter


def set_adapter(adapter: HindsightAdapter) -> None:
    global _adapter
    _adapter = adapter


def explain(analysis: AnalysisResult, context: ExplainContext) -> Explanation:
    """Generate an explanation and recommendations with evidence and memory citations."""
    adapter = get_adapter()
    valid_evidence_ids = {e.id for e in analysis.evidence}
    evidence_list = list(valid_evidence_ids)

    recalled_memories = []
    recalled_ids = []

    # 1. Recall memory if mode is LIVE
    if context.memory_mode == MemoryMode.LIVE:
        bank_name = adapter.get_bank_name(context.scenario, is_demo=True)
        query = f"sales commission incentive discount complaint cancellation {context.policy_id}"
        raw_recalled = adapter.recall(bank_name, query, as_of=context.as_of, limit=3)
        recalled_memories = filter_memories_by_as_of(raw_recalled, as_of=context.as_of)
        recalled_ids = [m.id for m in recalled_memories]

    # 2. Build tokenized templates
    (
        summary_tmpl,
        hypothesis_tmpl,
        supporting_tmpl,
        conflicting_tmpl,
        alt_tmpl,
        recs,
        template_dict,
    ) = build_template_explanation(analysis, evidence_list, recalled_ids)

    # 3. Sanitize recommendation citations
    valid_recalled_set = set(recalled_ids)
    sanitized_recs = sanitize_recommendations(recs, valid_evidence_ids, valid_recalled_set)

    # 4. Resolve tokens for display fields
    token_dict = build_token_dict(analysis)
    resolved_summary = resolve_tokens(summary_tmpl, token_dict)
    resolved_hypothesis = resolve_tokens(hypothesis_tmpl, token_dict)
    resolved_supporting = [resolve_tokens(p, token_dict) for p in supporting_tmpl]
    resolved_conflicting = [resolve_tokens(p, token_dict) for p in conflicting_tmpl]
    resolved_alt = [resolve_tokens(a, token_dict) for a in alt_tmpl]

    # 5. Determine source and status
    if context.memory_mode == MemoryMode.OFF:
        explanation_source = ExplanationSource.TEMPLATE
        memory_status = MemoryStatus.UNAVAILABLE
    elif adapter.is_live:
        explanation_source = ExplanationSource.REFLECT
        memory_status = MemoryStatus.LIVE
    elif recalled_memories:
        explanation_source = ExplanationSource.REFLECT
        memory_status = MemoryStatus.FIXTURE
    else:
        explanation_source = ExplanationSource.TEMPLATE
        memory_status = MemoryStatus.UNAVAILABLE

    return Explanation(
        summary=resolved_summary,
        hypothesis=resolved_hypothesis,
        supporting_points=resolved_supporting,
        conflicting_points=resolved_conflicting,
        alternatives=resolved_alt,
        recommendations=sanitized_recs,
        recalled=recalled_memories,
        explanation_source=explanation_source,
        memory_status=memory_status,
        validation_error_codes=[],
        template_text=template_dict,
    )


def retain_outcome(outcome: Outcome) -> RetentionResult:
    """Retain a management outcome in the scenario's memory bank."""
    adapter = get_adapter()
    # Scenarios are tracked by incident prefix or default demo bank
    scenario = "default"
    if outcome.incident_id and "-" in outcome.incident_id:
        parts = outcome.incident_id.split("-")
        if len(parts) >= 2:
            scenario = parts[1]
    bank_name = adapter.get_bank_name(scenario, is_demo=True)
    return adapter.retain_outcome(bank_name, outcome)


def seed_history(incidents: list[HistoricalIncident], scenario: str = "default") -> SeedResult:
    """Seed historical incident memory records into the demo memory bank."""
    adapter = get_adapter()
    bank_name = adapter.get_bank_name(scenario, is_demo=True)
    return adapter.seed_incidents(bank_name, incidents)


def reset_demo_bank(scenario: str) -> ResetResult:
    """Reset the demo memory bank for a given scenario."""
    adapter = get_adapter()
    return adapter.reset_demo_bank(scenario)
