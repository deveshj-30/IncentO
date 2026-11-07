"""Compare month-end policy deals with other policy deals at a fixed as-of time.

All business metrics come from dataset records. Text and memory services consume
the result but do not participate in these calculations.
"""

from __future__ import annotations

import calendar
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import NormalDist, mean, variance

from app.core.schemas import (
    AlternativeExplanation,
    AnalysisResult,
    Cancellation,
    CohortCounts,
    Dataset,
    Deal,
    Evidence,
    Interval,
    MetricName,
    MetricResult,
    MetricStatus,
    Policy,
    SourceType,
    Theme,
    Thresholds,
    Ticket,
)

COMPARISON_ID = "month-end-v1"
WINDOW = timedelta(days=30)
Z_95 = NormalDist().inv_cdf(0.975)


def _is_month_end(closed_at: datetime, days: int) -> bool:
    date = closed_at.astimezone(UTC).date()
    last_day = calendar.monthrange(date.year, date.month)[1]
    return date.day > last_day - days


def _wilson(successes: int, total: int) -> tuple[float, float]:
    proportion = successes / total
    z2 = Z_95 * Z_95
    denominator = 1 + z2 / total
    center = (proportion + z2 / (2 * total)) / denominator
    radius = Z_95 * math.sqrt(proportion * (1 - proportion) / total + z2 / (4 * total * total))
    return max(0.0, center - radius / denominator), min(1.0, center + radius / denominator)


def _rate_interval(first_hits: int, first_n: int, second_hits: int, second_n: int) -> Interval:
    """Newcombe hybrid-score interval for a difference of independent rates."""
    first = first_hits / first_n
    second = second_hits / second_n
    first_lower, first_upper = _wilson(first_hits, first_n)
    second_lower, second_upper = _wilson(second_hits, second_n)
    gap = first - second
    lower = gap - math.hypot(first - first_lower, second_upper - second)
    upper = gap + math.hypot(first_upper - first, second - second_lower)
    return Interval(lower=max(-1.0, lower), upper=min(1.0, upper), method="newcombe_hybrid_score")


def _mean_interval(first: list[float], second: list[float]) -> Interval:
    gap = mean(first) - mean(second)
    first_variance = variance(first) if len(first) > 1 else 0.0
    second_variance = variance(second) if len(second) > 1 else 0.0
    radius = Z_95 * math.sqrt(first_variance / len(first) + second_variance / len(second))
    return Interval(
        lower=max(-1.0, gap - radius),
        upper=min(1.0, gap + radius),
        method="normal_difference_of_means",
    )


def _status(
    gap: float | None,
    interval: Interval | None,
    baseline: float | None,
    first_n: int,
    second_n: int,
    thresholds: Thresholds,
) -> tuple[MetricStatus, list[str]]:
    if first_n < thresholds.min_group_size or second_n < thresholds.min_group_size:
        return MetricStatus.INSUFFICIENT_DATA, [
            f"Each group needs at least {thresholds.min_group_size} eligible deals."
        ]
    if gap is None or interval is None:
        return MetricStatus.INSUFFICIENT_DATA, ["A group has no observable denominator."]
    if gap < thresholds.gap_threshold:
        return MetricStatus.NO_SIGNAL, ["The month-end gap is below the plan threshold."]
    if baseline is None:
        return MetricStatus.WATCH, ["The pre-policy comparison is unavailable."]
    if interval.lower > 0 and gap - baseline >= thresholds.baseline_margin:
        return MetricStatus.FLAGGED, []
    return MetricStatus.WATCH, ["Cannot distinguish the gap from noise or a pre-existing pattern."]


def _valid_events(
    dataset: Dataset, deals: dict[str, Deal], as_of: datetime
) -> tuple[dict[str, list[Ticket]], dict[str, list[Cancellation]]]:
    tickets: dict[str, list[Ticket]] = defaultdict(list)
    cancellations: dict[str, list[Cancellation]] = defaultdict(list)
    seen: set[str] = set()
    for ticket in dataset.tickets:
        deal = deals.get(ticket.deal_id)
        if (
            ticket.ticket_id not in seen
            and deal is not None
            and ticket.customer_id == deal.customer_id
            and deal.closed_at <= ticket.created_at <= min(deal.closed_at + WINDOW, as_of)
        ):
            tickets[deal.deal_id].append(ticket)
            seen.add(ticket.ticket_id)
    seen.clear()
    for cancellation in dataset.cancellations:
        deal = deals.get(cancellation.deal_id)
        if (
            cancellation.cancellation_id not in seen
            and deal is not None
            and cancellation.customer_id == deal.customer_id
            and deal.closed_at <= cancellation.cancelled_at <= min(deal.closed_at + WINDOW, as_of)
        ):
            cancellations[deal.deal_id].append(cancellation)
            seen.add(cancellation.cancellation_id)
    return tickets, cancellations


def _event_customers(deals: list[Deal], events_by_deal: dict[str, list]) -> set[str]:
    return {deal.customer_id for deal in deals if events_by_deal.get(deal.deal_id)}


def _source_ids(deals: list[Deal], events_by_deal: dict[str, list], id_field: str) -> list[str]:
    return sorted(
        getattr(event, id_field) for deal in deals for event in events_by_deal.get(deal.deal_id, [])
    )[:5]


def _metric(
    name: MetricName,
    month_end: list[Deal],
    other: list[Deal],
    pre_month_end: list[Deal],
    pre_other: list[Deal],
    tickets: dict[str, list[Ticket]],
    cancellations: dict[str, list[Cancellation]],
    as_of: datetime,
    thresholds: Thresholds,
) -> MetricResult:
    reasons: list[str] = []
    if name == MetricName.DISCOUNT:
        first = [deal.discount for deal in month_end]
        second = [deal.discount for deal in other]
        pre_first = [deal.discount for deal in pre_month_end]
        pre_second = [deal.discount for deal in pre_other]
        first_n, second_n = len(first), len(second)
        first_value = mean(first) if first else None
        second_value = mean(second) if second else None
        baseline = mean(pre_first) - mean(pre_second) if pre_first and pre_second else None
        interval = _mean_interval(first, second) if first and second else None
        evidence_ids = [deal.deal_id for deal in sorted(month_end, key=lambda d: d.deal_id)[:5]]
        evidence_ids += [deal.deal_id for deal in sorted(other, key=lambda d: d.deal_id)[:2]]
        window_days = None
    else:
        events = tickets if name == MetricName.COMPLAINT_30D else cancellations
        id_field = "ticket_id" if name == MetricName.COMPLAINT_30D else "cancellation_id"

        def mature(deals: list[Deal]) -> list[Deal]:
            return [deal for deal in deals if deal.closed_at + WINDOW <= as_of]

        first_deals, second_deals = mature(month_end), mature(other)
        pre_first_deals, pre_second_deals = mature(pre_month_end), mature(pre_other)
        first_n, second_n = len(first_deals), len(second_deals)
        first_hits = len(_event_customers(first_deals, events))
        second_hits = len(_event_customers(second_deals, events))
        first_value = first_hits / first_n if first_n else None
        second_value = second_hits / second_n if second_n else None
        pre_first_hits = len(_event_customers(pre_first_deals, events))
        pre_second_hits = len(_event_customers(pre_second_deals, events))
        baseline = (
            pre_first_hits / len(pre_first_deals) - pre_second_hits / len(pre_second_deals)
            if pre_first_deals and pre_second_deals
            else None
        )
        interval = (
            _rate_interval(first_hits, first_n, second_hits, second_n) if first_n and second_n else None
        )
        evidence_ids = _source_ids(first_deals, events, id_field)
        evidence_ids += _source_ids(second_deals, events, id_field)[:2]
        excluded = len(month_end) + len(other) - first_n - second_n
        if excluded:
            reasons.append(f"Excluded {excluded} deals without a full 30-day observation window.")
        window_days = 30
    gap = first_value - second_value if first_value is not None and second_value is not None else None
    status, decision_reasons = _status(gap, interval, baseline, first_n, second_n, thresholds)
    return MetricResult(
        name=name,
        status=status,
        month_end_value=first_value,
        other_value=second_value,
        gap=gap,
        gap_interval=interval,
        pre_policy_gap=baseline,
        month_end_n=first_n,
        other_n=second_n,
        window_days=window_days,
        reasons=reasons + decision_reasons,
        evidence_ids=evidence_ids,
    )


def _evidence_for(dataset: Dataset, ids: set[str], as_of: datetime) -> list[Evidence]:
    evidence: dict[str, Evidence] = {}
    for deal in dataset.deals:
        if deal.deal_id in ids and deal.closed_at <= as_of:
            evidence[deal.deal_id] = Evidence(
                id=deal.deal_id,
                source_type=SourceType.DEAL,
                timestamp=deal.closed_at,
                customer_id=deal.customer_id,
                deal_id=deal.deal_id,
            )
    for ticket in dataset.tickets:
        if ticket.ticket_id in ids and ticket.created_at <= as_of:
            evidence[ticket.ticket_id] = Evidence(
                id=ticket.ticket_id,
                source_type=SourceType.TICKET,
                timestamp=ticket.created_at,
                theme=ticket.theme,
                customer_id=ticket.customer_id,
                deal_id=ticket.deal_id,
                excerpt=ticket.excerpt,
            )
    for cancellation in dataset.cancellations:
        if cancellation.cancellation_id in ids and cancellation.cancelled_at <= as_of:
            evidence[cancellation.cancellation_id] = Evidence(
                id=cancellation.cancellation_id,
                source_type=SourceType.CANCELLATION,
                timestamp=cancellation.cancelled_at,
                theme=cancellation.theme,
                customer_id=cancellation.customer_id,
                deal_id=cancellation.deal_id,
                excerpt=cancellation.excerpt,
            )
    for incident in dataset.history:
        if incident.incident_id in ids and incident.occurred_at <= as_of:
            evidence[incident.incident_id] = Evidence(
                id=incident.incident_id,
                source_type=SourceType.INCIDENT,
                timestamp=incident.occurred_at,
                excerpt=incident.title,
            )
    return [evidence[source_id] for source_id in sorted(ids) if source_id in evidence]


def _outage_alternative(
    month_end: list[Deal], other: list[Deal], tickets: dict[str, list[Ticket]]
) -> list[AlternativeExplanation]:
    def outage_ids(deals: list[Deal]) -> list[str]:
        return sorted(
            ticket.ticket_id
            for deal in deals
            for ticket in tickets.get(deal.deal_id, [])
            if ticket.theme == Theme.OUTAGE
        )[:3]

    first, second = outage_ids(month_end), outage_ids(other)
    if not first or not second:
        return []
    return [
        AlternativeExplanation(
            id="shared-outage-window",
            label="Outage-themed complaints affected both cohorts in a shared service window.",
            evidence_ids=first + second,
        )
    ]


def analyze(dataset: Dataset, policy_id: str, as_of: datetime) -> AnalysisResult:
    """Return the fixed three-metric comparison, with traceable source evidence."""
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    as_of = as_of.astimezone(UTC)
    policies = [policy for policy in dataset.policies if policy.policy_id == policy_id]
    if not policies:
        raise ValueError(f"Unknown policy_id: {policy_id}")
    current = [policy for policy in policies if policy.effective_at <= as_of]
    policy: Policy = (
        max(current, key=lambda item: item.effective_at)
        if current
        else min(policies, key=lambda item: item.effective_at)
    )
    thresholds = Thresholds()
    scoped = [
        deal
        for deal in dataset.deals
        if deal.policy_id == policy.policy_id
        and deal.policy_version == policy.version
        and deal.segment == policy.segment
        and deal.channel == policy.channel
        and deal.closed_at <= as_of
    ]
    post = [deal for deal in scoped if deal.closed_at >= policy.effective_at]
    pre = [deal for deal in scoped if deal.closed_at < policy.effective_at]
    month_end = [deal for deal in post if _is_month_end(deal.closed_at, thresholds.month_end_days)]
    other = [deal for deal in post if not _is_month_end(deal.closed_at, thresholds.month_end_days)]
    pre_month_end = [deal for deal in pre if _is_month_end(deal.closed_at, thresholds.month_end_days)]
    pre_other = [deal for deal in pre if not _is_month_end(deal.closed_at, thresholds.month_end_days)]
    tickets, cancellations = _valid_events(dataset, {deal.deal_id: deal for deal in scoped}, as_of)
    metrics = [
        _metric(
            name,
            month_end,
            other,
            pre_month_end,
            pre_other,
            tickets,
            cancellations,
            as_of,
            thresholds,
        )
        for name in MetricName
    ]
    alternatives = _outage_alternative(month_end, other, tickets)
    cited = {source_id for metric in metrics for source_id in metric.evidence_ids}
    cited.update(source_id for alternative in alternatives for source_id in alternative.evidence_ids)
    evidence = _evidence_for(dataset, cited, as_of)
    evidence_by_id = {item.id: item for item in evidence}
    corroborating = {
        evidence_by_id[source_id].customer_id
        for metric in metrics
        if metric.status == MetricStatus.FLAGGED
        for source_id in metric.evidence_ids
        if source_id in evidence_by_id and evidence_by_id[source_id].customer_id is not None
    }

    def counts(label: str, deals: list[Deal]) -> CohortCounts:
        eligible = sum(deal.closed_at + WINDOW <= as_of for deal in deals)
        return CohortCounts(
            label=label,
            eligible=eligible,
            excluded_immature=len(deals) - eligible,
            total=len(deals),
        )

    insufficient = [
        f"{metric.name.value}: {reason}"
        for metric in metrics
        if metric.status == MetricStatus.INSUFFICIENT_DATA
        for reason in metric.reasons
    ]
    return AnalysisResult(
        policy_id=policy_id,
        policy_version=policy.version,
        scenario=dataset.meta.scenario,
        as_of=as_of,
        comparison_id=COMPARISON_ID,
        flagged=any(metric.status == MetricStatus.FLAGGED for metric in metrics) and len(corroborating) >= 2,
        metrics_checked=3,
        thresholds=thresholds,
        month_end=counts("Post-policy month-end", month_end),
        other=counts("Post-policy other", other),
        metrics=metrics,
        corroborating_customers=len(corroborating),
        alternatives=alternatives,
        evidence=evidence,
        insufficient_reasons=insufficient,
    )
