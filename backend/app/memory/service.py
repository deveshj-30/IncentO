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
    RecalledMemory,
    RecalledMemoryType,
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
    validate_structured_output,
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
                            "adjust_policy",
                            "pilot_guardrail",
                            "revert_change",
                            "collect_more_data",
                            "no_action",
                        ],
                    },
                    "action": {"type": "string"},
                    "rationale": {"type": "string"},
                    "success_metric": {"type": "string"},
                    "guardrail": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "history_influence": {"type": "array", "items": {"type": "string"}},
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
    # Recall direct candidates first
    raw_recalled = adapter.recall(bank_name, query, as_of=context.as_of, limit=3)
    if raw_recalled:
        recalled_memories = filter_memories_by_as_of(raw_recalled, as_of=context.as_of)

    token_dict = build_token_dict(analysis)
    structured_out = None

    if adapter.is_live:
        temp_ids = [m.id for m in recalled_memories]
        reflect_query = (
            f"Commission policy month-end incentive investigation (flagged={analysis.flagged}). "
            f"Available evidence IDs: {evidence_list[:10]}. Recalled memory IDs: {temp_ids}. "
            "Directives: Never cite unprovided IDs. Never cite a rejected hypothesis as history influence. "
            "Do NOT include raw digits (0-9) or percentages in summary, hypothesis, points, alternatives, "
            "action, or rationale. Refer to the policy as 'the policy'. "
            "Use metric tokens such as {{m:discount.gap}} and {{m:complaint_30d.gap}} "
            "instead of typing numbers. "
            "Fields must be strictly free of digits and percent signs."
        )
        structured_out, reflect_memories = adapter.reflect(
            bank_name, reflect_query, REFLECT_RESPONSE_SCHEMA, as_of=context.as_of
        )
        if reflect_memories:
            recalled_memories.extend(filter_memories_by_as_of(reflect_memories, as_of=context.as_of))

    # Deduplicate recalled memories by ID
    seen_ids: set[str] = set()
    deduped_memories: list[RecalledMemory] = []
    for m in recalled_memories:
        if m.id not in seen_ids:
            seen_ids.add(m.id)
            deduped_memories.append(m)
    recalled_memories = deduped_memories
    recalled_ids = [m.id for m in recalled_memories]
    valid_recalled_set = set(recalled_ids)
    rejected_ids = {
        m.id for m in recalled_memories if m.memory_type == RecalledMemoryType.REJECTED_HYPOTHESIS
    }

    # 3. If Reflect returned valid structured output, validate against contract rules
    if structured_out:
        is_valid, err = validate_structured_output(
            structured_out, token_dict, valid_evidence_ids, valid_recalled_set, rejected_ids
        )
        if not is_valid and adapter.is_live:
            # Plan requirement: retry once with validation errors listed before falling back
            log.info("Reflect output attempt 1 failed validation (%s); retrying with error feedback", err)
            retry_query = (
                f"{reflect_query}\n\nCRITICAL FIX: Your previous response failed contract validation: {err}. "
                "You must remove ALL digits (0-9) and percent signs. Use tokens like {{m:discount.gap}}."
            )
            structured_out_retry, _ = adapter.reflect(
                bank_name, retry_query, REFLECT_RESPONSE_SCHEMA, as_of=context.as_of
            )
            if structured_out_retry:
                is_valid_retry, err_retry = validate_structured_output(
                    structured_out_retry, token_dict, valid_evidence_ids, valid_recalled_set, rejected_ids
                )
                if is_valid_retry:
                    structured_out = structured_out_retry
                    is_valid = True
                else:
                    log.warning("Reflect retry also failed validation: %s", err_retry)

        if is_valid:
            parsed_recs = []
            for r in structured_out.get("recommendations", []):
                try:
                    action_type = ActionType(r.get("action_type", "pilot_guardrail"))
                except ValueError:
                    action_type = ActionType.PILOT_GUARDRAIL
                clean_evidence = [e for e in r.get("evidence_ids", []) if e in valid_evidence_ids]
                clean_influence = [
                    h for h in r.get("history_influence", [])
                    if h in valid_recalled_set and h not in rejected_ids
                ]
                parsed_recs.append(
                    Recommendation(
                        action_type=action_type,
                        action=resolve_tokens(r.get("action", ""), token_dict),
                        rationale=resolve_tokens(r.get("rationale", ""), token_dict),
                        evidence_ids=clean_evidence,
                        success_metric=r.get("success_metric", "Monitor churn metrics within baseline."),
                        guardrail=r.get("guardrail", "Alert when cancellation gap exceeds threshold."),
                        history_influence=clean_influence,
                    )
                )
            return Explanation(
                summary=resolve_tokens(structured_out.get("summary", ""), token_dict),
                hypothesis=resolve_tokens(structured_out.get("hypothesis", ""), token_dict),
                supporting_points=[
                    resolve_tokens(p, token_dict) for p in structured_out.get("supporting_points", [])
                ],
                conflicting_points=[
                    resolve_tokens(p, token_dict) for p in structured_out.get("conflicting_points", [])
                ],
                alternatives=[
                    resolve_tokens(a, token_dict) for a in structured_out.get("alternatives", [])
                ],
                recommendations=parsed_recs,
                recalled=recalled_memories,
                explanation_source=ExplanationSource.REFLECT,
                memory_status=MemoryStatus.LIVE,
                validation_error_codes=[],
                template_text={},
            )
        else:
            log.warning("Reflect output rejected by contract validation: %s; using template fallback", err)

    # 4. Fallback to tokenized template
    (
        summary_tmpl,
        hypothesis_tmpl,
        supporting_tmpl,
        conflicting_tmpl,
        alt_tmpl,
        recs,
        template_dict,
    ) = build_template_explanation(analysis, evidence_list, recalled_memories)

    sanitized_recs = sanitize_recommendations(recs, valid_evidence_ids, valid_recalled_set)

    if adapter.is_live and recalled_memories:
        memory_status = MemoryStatus.LIVE
    elif adapter.simulation_enabled and recalled_memories:
        memory_status = MemoryStatus.FIXTURE
    else:
        memory_status = MemoryStatus.UNAVAILABLE
        recalled_memories = []

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
