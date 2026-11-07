"""Public memory module entry points called by the core orchestrator."""

import logging
from typing import Any

from app.core.schemas import (
    ActionType,
    AnalysisResult,
    ExplainContext,
    Explanation,
    ExplanationSource,
    HistoricalIncident,
    MemoryMode,
    MemoryStatus,
    Outcome,
    Recommendation,
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


REFLECT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "hypothesis": {"type": "string"},
        "supporting_points": {"type": "array", "items": {"type": "string"}},
        "conflicting_points": {"type": "array", "items": {"type": "string"}},
        "alternatives": {"type": "array", "items": {"type": "string"}},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "enum": [
                            "retrain_reps",
                            "commission_clawback",
                            "adjust_quota",
                            "adjust_approval",
                            "modify_terms",
                            "monitor",
                        ],
                    },
                    "action": {"type": "string"},
                    "rationale": {"type": "string"},
                    "success_metric": {"type": "string"},
                    "guardrail": {"type": "string"},
                },
                "required": ["action_type", "action", "rationale", "success_metric", "guardrail"],
            },
        },
    },
    "required": ["summary", "hypothesis", "recommendations"],
}


def explain(analysis: AnalysisResult, context: ExplainContext) -> Explanation:
    """Generate an explanation and recommendations with evidence and memory citations."""
    adapter = get_adapter()
    valid_evidence_ids = {e.id for e in analysis.evidence}
    evidence_list = list(valid_evidence_ids)

    # 1. When memory_mode is OFF: strictly no recall, template explanation
    if context.memory_mode == MemoryMode.OFF:
        (
            summary_tmpl,
            hypothesis_tmpl,
            supporting_tmpl,
            conflicting_tmpl,
            alt_tmpl,
            recs,
            template_dict,
        ) = build_template_explanation(analysis, evidence_list, [])
        token_dict = build_token_dict(analysis)
        sanitized_recs = sanitize_recommendations(recs, valid_evidence_ids, set())
        return Explanation(
            summary=resolve_tokens(summary_tmpl, token_dict),
            hypothesis=resolve_tokens(hypothesis_tmpl, token_dict),
            supporting_points=[resolve_tokens(p, token_dict) for p in supporting_tmpl],
            conflicting_points=[resolve_tokens(p, token_dict) for p in conflicting_tmpl],
            alternatives=[resolve_tokens(a, token_dict) for a in alt_tmpl],
            recommendations=sanitized_recs,
            recalled=[],
            explanation_source=ExplanationSource.TEMPLATE,
            memory_status=MemoryStatus.UNAVAILABLE,
            validation_error_codes=[],
            template_text=template_dict,
        )

    # 2. When memory_mode is LIVE
    bank_name = adapter.get_bank_name(context.scenario, is_demo=True)
    query = (
        f"Sales commission policy {context.policy_id} month-end incentive impact: "
        f"flagged={analysis.flagged}."
    )

    recalled_memories = []
    structured_out = None

    if adapter.is_live:
        structured_out, reflect_memories = adapter.reflect(
            bank_name, query, REFLECT_RESPONSE_SCHEMA, as_of=context.as_of
        )
        if reflect_memories:
            recalled_memories = filter_memories_by_as_of(reflect_memories, as_of=context.as_of)

    if not recalled_memories:
        # Fallback to direct recall
        raw_recalled = adapter.recall(bank_name, query, as_of=context.as_of, limit=3)
        recalled_memories = filter_memories_by_as_of(raw_recalled, as_of=context.as_of)

    recalled_ids = [m.id for m in recalled_memories]
    valid_recalled_set = set(recalled_ids)

    # 3. If Reflect returned valid structured output, use it
    if structured_out:
        parsed_recs = []
        for r in structured_out.get("recommendations", []):
            try:
                action_type = ActionType(r.get("action_type", "monitor"))
            except ValueError:
                action_type = ActionType.MONITOR
            parsed_recs.append(
                Recommendation(
                    action_type=action_type,
                    action=r.get("action", ""),
                    rationale=r.get("rationale", ""),
                    evidence_ids=evidence_list[:3],
                    success_metric=r.get("success_metric", "Monitor churn metrics within baseline."),
                    guardrail=r.get("guardrail", "Alert when cancellation gap exceeds threshold."),
                    history_influence=recalled_ids[:2],
                )
            )
        sanitized_recs = sanitize_recommendations(parsed_recs, valid_evidence_ids, valid_recalled_set)
        return Explanation(
            summary=structured_out.get("summary", ""),
            hypothesis=structured_out.get("hypothesis", ""),
            supporting_points=structured_out.get("supporting_points", []),
            conflicting_points=structured_out.get("conflicting_points", []),
            alternatives=structured_out.get("alternatives", []),
            recommendations=sanitized_recs,
            recalled=recalled_memories,
            explanation_source=ExplanationSource.REFLECT,
            memory_status=MemoryStatus.LIVE,
            validation_error_codes=[],
            template_text={},
        )

    # 4. Fallback to tokenized template
    (
        summary_tmpl,
        hypothesis_tmpl,
        supporting_tmpl,
        conflicting_tmpl,
        alt_tmpl,
        recs,
        template_dict,
    ) = build_template_explanation(analysis, evidence_list, recalled_ids)

    sanitized_recs = sanitize_recommendations(recs, valid_evidence_ids, valid_recalled_set)
    token_dict = build_token_dict(analysis)

    if adapter.is_live and recalled_memories:
        memory_status = MemoryStatus.LIVE
    elif adapter.simulation_enabled and recalled_memories:
        memory_status = MemoryStatus.FIXTURE
    else:
        memory_status = MemoryStatus.UNAVAILABLE

    return Explanation(
        summary=resolve_tokens(summary_tmpl, token_dict),
        hypothesis=resolve_tokens(hypothesis_tmpl, token_dict),
        supporting_points=[resolve_tokens(p, token_dict) for p in supporting_tmpl],
        conflicting_points=[resolve_tokens(p, token_dict) for p in conflicting_tmpl],
        alternatives=[resolve_tokens(a, token_dict) for a in alt_tmpl],
        recommendations=sanitized_recs,
        recalled=recalled_memories,
        explanation_source=ExplanationSource.TEMPLATE,
        memory_status=memory_status,
        validation_error_codes=[],
        template_text=template_dict,
    )


def retain_outcome(outcome: Outcome, scenario: str) -> RetentionResult:
    """Retain a management outcome into the designated scenario's demo memory bank."""
    adapter = get_adapter()
    bank_name = adapter.get_bank_name(scenario, is_demo=True)
    return adapter.retain_outcome(bank_name, outcome)


def seed_history(incidents: list[HistoricalIncident], scenario: str) -> SeedResult:
    """Seed historical incident memory records into the designated scenario's demo memory bank."""
    adapter = get_adapter()
    bank_name = adapter.get_bank_name(scenario, is_demo=True)
    return adapter.seed_incidents(bank_name, incidents)


def reset_demo_bank(scenario: str) -> ResetResult:
    """Reset the demo memory bank for a given scenario."""
    adapter = get_adapter()
    return adapter.reset_demo_bank(scenario)
