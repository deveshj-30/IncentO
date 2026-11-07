"""Validation, token resolution, and chronology enforcement for memory and explanations."""

import re
from datetime import datetime
from typing import Any

from app.core.schemas import ActionType, AnalysisResult, RecalledMemory, Recommendation

_TOKEN_RE = re.compile(r"\{\{([mt]):([a-zA-Z0-9_.]+)\}\}")


def _format_val(val: Any) -> str:
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:.1%}" if abs(val) <= 1.0 else f"{val:.2f}"
    return str(val)


def build_token_dict(analysis: AnalysisResult) -> dict[str, str]:
    """Map token keys (e.g. 'm:discount.gap', 't:gap_threshold') to formatted strings."""
    tokens: dict[str, str] = {}

    # Threshold constants
    tokens["t:gap_threshold"] = _format_val(analysis.thresholds.gap_threshold)
    tokens["t:baseline_margin"] = _format_val(analysis.thresholds.baseline_margin)
    tokens["t:min_group_size"] = str(analysis.thresholds.min_group_size)
    tokens["t:month_end_days"] = str(analysis.thresholds.month_end_days)

    # Metrics
    for m in analysis.metrics:
        prefix = f"m:{m.name.value}"
        tokens[f"{prefix}.month_end_value"] = _format_val(m.month_end_value)
        tokens[f"{prefix}.other_value"] = _format_val(m.other_value)
        tokens[f"{prefix}.gap"] = _format_val(m.gap)
        tokens[f"{prefix}.month_end_n"] = str(m.month_end_n)
        tokens[f"{prefix}.other_n"] = str(m.other_n)
        tokens[f"{prefix}.pre_policy_gap"] = _format_val(m.pre_policy_gap)
        tokens[f"{prefix}.status"] = m.status.value
        if m.gap_interval is not None:
            tokens[f"{prefix}.gap_lower"] = _format_val(m.gap_interval.lower)
            tokens[f"{prefix}.gap_upper"] = _format_val(m.gap_interval.upper)
        else:
            tokens[f"{prefix}.gap_lower"] = "N/A"
            tokens[f"{prefix}.gap_upper"] = "N/A"

    return tokens


def resolve_tokens(text: str, token_dict: dict[str, str]) -> str:
    """Replace {{m:...}} and {{t:...}} tokens with their formatted values."""
    if not text:
        return text

    def _replace(match: re.Match[str]) -> str:
        key = f"{match.group(1)}:{match.group(2)}"
        return token_dict.get(key, match.group(0))

    return _TOKEN_RE.sub(_replace, text)


def filter_memories_by_as_of(
    memories: list[RecalledMemory], as_of: datetime
) -> list[RecalledMemory]:
    """Strictly filter out any memory dated strictly after as_of cutoff."""
    return [m for m in memories if m.event_time <= as_of]


def sanitize_recommendations(
    recommendations: list[Recommendation],
    valid_evidence_ids: set[str],
    valid_recalled_ids: set[str],
) -> list[Recommendation]:
    """Ensure all recommendation citations only reference known evidence and recalled IDs."""
    sanitized: list[Recommendation] = []
    for rec in recommendations:
        clean_evidence = [eid for eid in rec.evidence_ids if eid in valid_evidence_ids]
        clean_influence = [mid for mid in rec.history_influence if mid in valid_recalled_ids]
        sanitized.append(
            Recommendation(
                action_type=rec.action_type,
                action=rec.action,
                rationale=rec.rationale,
                evidence_ids=clean_evidence,
                success_metric=rec.success_metric,
                guardrail=rec.guardrail,
                history_influence=clean_influence,
            )
        )
    return sanitized


def validate_explanation_text(text: str, token_dict: dict[str, str]) -> tuple[bool, str | None]:
    """Validate a text field per the explanation number and safety rules:
    - All tokens must resolve against token_dict; unknown tokens reject.
    - After tokens are stripped, text must not contain digits (0-9), '%', or 'percent'.
    - Must not contain URLs, HTML, markdown links, or code fences.
    """
    if not text:
        return True, None

    # Free-text security checks: no URLs, HTML, markdown links, code fences
    if "```" in text or ("<" in text and ">" in text):
        return False, "contains_code_or_html"
    if "http://" in text or "https://" in text or "www." in text:
        return False, "contains_url"
    if re.search(r"\[.*?\]\(.*?\)", text):
        return False, "contains_markdown_link"

    # Check that all tokens in the text resolve against token_dict
    for match in _TOKEN_RE.finditer(text):
        key = f"{match.group(1)}:{match.group(2)}"
        if key not in token_dict:
            return False, f"unknown_token:{key}"

    # Strip tokens before checking for numbers
    stripped = _TOKEN_RE.sub("", text)

    # Number rules: no digits, %, or 'percent'
    if any(ch.isdigit() for ch in stripped):
        return False, "contains_digits"
    if "%" in stripped or "percent" in stripped.lower():
        return False, "contains_percent"

    return True, None


def validate_structured_output(
    data: dict[str, Any],
    token_dict: dict[str, str],
    valid_evidence_ids: set[str],
    valid_recalled_ids: set[str],
) -> tuple[bool, str | None]:
    """Validate Reflect structured output against contract rules:
    - summary, hypothesis, supporting_points, conflicting_points, alternatives, rec action & rationale
      must pass validate_explanation_text.
    - recommendations must have valid action_type enum, evidence_ids subset of valid_evidence_ids,
      and history_influence subset of valid_recalled_ids.
    """
    if not isinstance(data, dict):
        return False, "not_a_dict"

    for field in ("summary", "hypothesis"):
        val = data.get(field, "")
        ok, err = validate_explanation_text(val, token_dict)
        if not ok:
            return False, f"{field}:{err}"

    for list_field in ("supporting_points", "conflicting_points", "alternatives"):
        items = data.get(list_field, [])
        if not isinstance(items, list):
            return False, f"{list_field}:not_a_list"
        for item in items:
            if isinstance(item, str):
                ok, err = validate_explanation_text(item, token_dict)
                if not ok:
                    return False, f"{list_field}:{err}"

    recs = data.get("recommendations", [])
    if not isinstance(recs, list) or not recs:
        return False, "missing_recommendations"

    valid_actions = {a.value for a in ActionType}
    for rec in recs:
        if not isinstance(rec, dict):
            return False, "rec_not_a_dict"
        action_type = rec.get("action_type")
        if action_type not in valid_actions:
            return False, f"invalid_action_type:{action_type}"

        for tf in ("action", "rationale"):
            val = rec.get(tf, "")
            ok, err = validate_explanation_text(val, token_dict)
            if not ok:
                return False, f"rec_{tf}:{err}"

        # Citation subset validation
        eids = rec.get("evidence_ids", [])
        if not set(eids).issubset(valid_evidence_ids):
            return False, "unknown_evidence_citation"

        hids = rec.get("history_influence", [])
        if not set(hids).issubset(valid_recalled_ids):
            return False, "unknown_history_citation"

    return True, None
