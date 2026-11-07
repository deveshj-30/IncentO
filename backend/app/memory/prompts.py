"""Explanation templates, tokenized strings, and prompt construction."""

from app.core.schemas import (
    ActionType,
    AnalysisResult,
    MetricName,
    MetricStatus,
    Recommendation,
)


def build_template_explanation(
    analysis: AnalysisResult,
    evidence_ids: list[str],
    recalled_ids: list[str] | None = None,
) -> tuple[str, str, list[str], list[str], list[str], list[Recommendation], dict[str, str]]:
    """Build tokenized explanation components and recommendations based on analysis signals.

    Returns:
        (summary, hypothesis, supporting, conflicting, alternatives, recommendations, template_dict)
    """
    recalled_ids = recalled_ids or []
    metrics_by_name = {m.name: m for m in analysis.metrics}
    cancel = metrics_by_name.get(MetricName.CANCEL_30D)

    is_flagged = analysis.flagged
    has_insufficient = any(m.status == MetricStatus.INSUFFICIENT_DATA for m in analysis.metrics)

    # Use first 2 evidence IDs if available
    top_evidence = evidence_ids[:2]

    if has_insufficient and not is_flagged:
        summary_tmpl = (
            "Cohort volume is currently below minimum observation thresholds "
            "(minimum {{t:min_group_size}} deals required). More observations needed."
        )
        hypothesis_tmpl = (
            "Data is currently insufficient to determine whether the acquisition policy "
            "is affecting deal quality."
        )
        supporting_tmpl: list[str] = []
        conflicting_tmpl: list[str] = []
        alt_tmpl = ["Immature cohort observation windows may be masking downstream effects."]
        recs = [
            Recommendation(
                action_type=ActionType.COLLECT_MORE_DATA,
                action="Continue tracking deal cohorts until sample sizes reach statistical threshold.",
                rationale="Insufficient cohort volume prevents conclusive evaluation.",
                evidence_ids=top_evidence,
                success_metric="Observe at least {{t:min_group_size}} deals per cohort group",
                guardrail="Do not alter commission policies without confirmed cohort divergence",
                history_influence=recalled_ids[:1],
            )
        ]
    elif is_flagged:
        summary_tmpl = (
            "Month-end deals show a discount gap of {{m:discount.gap}} and a 30-day complaint gap "
            "of {{m:complaint_30d.gap}}, above the {{t:gap_threshold}} threshold."
        )
        hypothesis_tmpl = (
            "The acquisition bonus may be associated with heavier discounting and poorer-fit deals "
            "at month end; this does not establish causation."
        )
        supporting_tmpl = [
            "Discount gap {{m:discount.gap}} with confidence interval "
            "{{m:discount.gap_lower}} to {{m:discount.gap_upper}}."
        ]
        conflicting_tmpl = []
        if cancel and cancel.status in (MetricStatus.WATCH, MetricStatus.NO_SIGNAL):
            conflicting_tmpl.append(
                "Cancellations are currently within expected limits: gap {{m:cancel_30d.gap}}."
            )

        alt_tmpl = [
            "Natural enterprise procurement cycles often cluster renewals and purchases "
            "at quarter and month end."
        ]

        # Recommendation tailored to memory or policy adjustment
        if recalled_ids:
            recs = [
                Recommendation(
                    action_type=ActionType.PILOT_GUARDRAIL,
                    action=(
                        "Pilot a discount approval step on month-end deals for one quarter "
                        "rather than abrupt bonus cancellation."
                    ),
                    rationale=(
                        "Discount and early complaint gaps are flagged; past incident history indicates "
                        "abrupt policy cancellation causes seller churn and pipeline disruption."
                    ),
                    evidence_ids=top_evidence,
                    success_metric="Month-end complaint gap under 10 points within two quarters",
                    guardrail="Do not slow deals below the approval service level of two business days",
                    history_influence=recalled_ids[:1],
                )
            ]
        else:
            recs = [
                Recommendation(
                    action_type=ActionType.REVERT_CHANGE,
                    action="Revert or suspend the month-end acquisition bonus policy.",
                    rationale="Discount and early complaint gaps are flagged above threshold.",
                    evidence_ids=top_evidence,
                    success_metric="Month-end complaint gap under 10 points within two quarters",
                    guardrail="Do not slow deals below the approval service level of two business days",
                    history_influence=[],
                )
            ]
    else:
        summary_tmpl = (
            "Month-end deals show no statistically significant divergence from baseline "
            "(discount gap {{m:discount.gap}}, complaint gap {{m:complaint_30d.gap}})."
        )
        hypothesis_tmpl = (
            "Current deal metrics show no clear association between the acquisition policy and poor deal fit."
        )
        supporting_tmpl = [
            "All evaluated metrics remain within the {{t:gap_threshold}} tolerance band."
        ]
        conflicting_tmpl = []
        alt_tmpl = ["Early indicators may appear in longer retention windows beyond 30 days."]
        recs = [
            Recommendation(
                action_type=ActionType.NO_ACTION,
                action="Maintain current incentive structure while continuing standard quarterly monitoring.",
                rationale="Metrics remain within acceptable historical tolerance.",
                evidence_ids=top_evidence,
                success_metric="Sustain current cohort alignment across the upcoming quarter",
                guardrail="Review immediately if month-end cancellation gap exceeds 10 percentage points",
                history_influence=recalled_ids[:1],
            )
        ]

    template_dict = {
        "summary": summary_tmpl,
        "hypothesis": hypothesis_tmpl,
    }

    return summary_tmpl, hypothesis_tmpl, supporting_tmpl, conflicting_tmpl, alt_tmpl, recs, template_dict
