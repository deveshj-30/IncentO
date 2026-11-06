"""Source of truth for the IncentiveTrap v1 contracts (P2 owns this file).

Contracts under ``contracts/`` and the frontend types are generated from these
models; never hand-edit the generated files. P3 and P4 import these models and
must not edit them. Slice A (frozen at G1) covers AnalysisResult, the
Investigation/Explanation response, the error shape and the conventions below.

Conventions
- IDs are stable strings; never join on display names.
- Timestamps are timezone-aware and serialized in UTC (``...Z``).
- Money is integer minor units plus an ISO currency code.
- Rates, discounts and intervals are fractions from 0 to 1; gaps are fraction
  differences (0.15 means 15 percentage points).
- Missing values are explicit ``None``, never 0.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]
Fraction = Annotated[float, Field(ge=0.0, le=1.0)]
SignedFraction = Annotated[float, Field(ge=-1.0, le=1.0)]
Id = Annotated[str, Field(min_length=1, max_length=128)]


class Contract(BaseModel):
    """Base for every contract model: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


# --- Enumerations ---------------------------------------------------------


class Theme(StrEnum):
    MISSING_FEATURE = "missing_feature"
    ONBOARDING_DIFFICULTY = "onboarding_difficulty"
    PRICING_DISPUTE = "pricing_dispute"
    OUTAGE = "outage"
    OTHER = "other"


class SourceType(StrEnum):
    DEAL = "deal"
    TICKET = "ticket"
    CANCELLATION = "cancellation"
    INCIDENT = "incident"


class MetricName(StrEnum):
    """The three fixed metrics; also the ``{{m:<name>.<field>}}`` token prefixes."""

    DISCOUNT = "discount"
    COMPLAINT_30D = "complaint_30d"
    CANCEL_30D = "cancel_30d"


class MetricStatus(StrEnum):
    FLAGGED = "flagged"
    WATCH = "watch"
    NO_SIGNAL = "no_signal"
    INSUFFICIENT_DATA = "insufficient_data"


class MemoryMode(StrEnum):
    LIVE = "live"
    OFF = "off"


class MemoryStatus(StrEnum):
    LIVE = "live"
    UNAVAILABLE = "unavailable"
    FIXTURE = "fixture"


class ExplanationSource(StrEnum):
    REFLECT = "reflect"
    TEMPLATE = "template"


class ActionType(StrEnum):
    ADJUST_POLICY = "adjust_policy"
    PILOT_GUARDRAIL = "pilot_guardrail"
    REVERT_CHANGE = "revert_change"
    COLLECT_MORE_DATA = "collect_more_data"
    NO_ACTION = "no_action"


class RecalledMemoryType(StrEnum):
    FACT = "fact"
    HYPOTHESIS = "hypothesis"
    REJECTED_HYPOTHESIS = "rejected_hypothesis"
    DECISION = "decision"
    MEASURED_RESULT = "measured_result"


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    AS_OF_BEFORE_MEMORY = "as_of_before_memory"
    RETENTION_PENDING = "retention_pending"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    NOT_IMPLEMENTED = "not_implemented"
    INTERNAL_ERROR = "internal_error"


# --- Shared building blocks -----------------------------------------------


class Money(Contract):
    amount_minor: int
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class Interval(Contract):
    """Uncertainty interval (fractions); ``level`` is the confidence level used."""

    lower: SignedFraction
    upper: SignedFraction
    method: str
    level: Annotated[float, Field(gt=0.0, lt=1.0)] = 0.95


class Evidence(Contract):
    """A source record behind a finding. ``excerpt`` is for display only and is
    never sent to a model; the model sees ``id``, ``source_type``, ``timestamp``
    and ``theme`` only."""

    id: Id
    source_type: SourceType
    timestamp: UtcDatetime
    theme: Theme | None = None
    customer_id: Id | None = None
    deal_id: Id | None = None
    excerpt: Annotated[str, Field(max_length=500)] | None = None


class CohortCounts(Contract):
    label: str
    eligible: Annotated[int, Field(ge=0)]
    excluded_immature: Annotated[int, Field(ge=0)] = 0
    total: Annotated[int, Field(ge=0)]


class MetricResult(Contract):
    name: MetricName
    status: MetricStatus
    month_end_value: Fraction | None
    other_value: Fraction | None
    gap: SignedFraction | None
    gap_interval: Interval | None
    pre_policy_gap: SignedFraction | None
    month_end_n: Annotated[int, Field(ge=0)]
    other_n: Annotated[int, Field(ge=0)]
    window_days: Annotated[int, Field(ge=0)] | None = None
    reasons: list[str] = Field(default_factory=list)
    evidence_ids: list[Id] = Field(default_factory=list)


class AlternativeExplanation(Contract):
    id: Id
    label: str
    evidence_ids: list[Id] = Field(default_factory=list)


class Thresholds(Contract):
    """Plan thresholds, exposed through ``{{t:<name>}}`` tokens."""

    gap_threshold: Fraction = 0.10
    baseline_margin: Fraction = 0.10
    min_group_size: Annotated[int, Field(ge=1)] = 30
    month_end_days: Annotated[int, Field(ge=1)] = 5


class AnalysisResult(Contract):
    """Output of P3's ``analyze(dataset, policy_id, as_of)``; deterministic."""

    policy_id: Id
    policy_version: Id
    scenario: Id
    as_of: UtcDatetime
    comparison_id: Id
    flagged: bool
    metrics_checked: Annotated[int, Field(ge=0)] = 3
    thresholds: Thresholds = Field(default_factory=Thresholds)
    month_end: CohortCounts
    other: CohortCounts
    metrics: list[MetricResult]
    corroborating_customers: Annotated[int, Field(ge=0)] = 0
    alternatives: list[AlternativeExplanation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    insufficient_reasons: list[str] = Field(default_factory=list)


# --- Explanation / Investigation ------------------------------------------


class RecalledMemory(Contract):
    """A memory that shaped a recommendation (``history_influence`` target)."""

    id: Id
    memory_type: RecalledMemoryType
    event_time: UtcDatetime
    incident_id: Id | None = None
    summary: str


class Recommendation(Contract):
    action_type: ActionType
    action: str
    rationale: str
    evidence_ids: list[Id] = Field(default_factory=list)
    success_metric: str = Field(description="Proposed target (not calculated).")
    guardrail: str = Field(description="Proposed target (not calculated).")
    history_influence: list[Id] = Field(default_factory=list)


class Explanation(Contract):
    """Output of P4's ``explain(analysis, context)``. Text fields are resolved
    for display; ``template_text`` keeps the tokenized originals for audit."""

    summary: str
    hypothesis: str
    supporting_points: list[str] = Field(default_factory=list)
    conflicting_points: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation]
    recalled: list[RecalledMemory] = Field(default_factory=list)
    explanation_source: ExplanationSource
    memory_status: MemoryStatus
    validation_error_codes: list[str] = Field(default_factory=list)
    template_text: dict[str, str] = Field(default_factory=dict)


class InvestigationRequest(Contract):
    policy_id: Id
    scenario: Id
    as_of: UtcDatetime
    memory_mode: MemoryMode = MemoryMode.LIVE
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128)]


class Investigation(Contract):
    """One stored run; ``run_id`` is the investigation ID."""

    run_id: Id
    policy_id: Id
    scenario: Id
    as_of: UtcDatetime
    created_at: UtcDatetime
    memory_mode: MemoryMode
    incident_id: Id | None
    analysis_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    synthetic: bool = True
    analysis: AnalysisResult
    explanation: Explanation


class InvestigationSummary(Contract):
    run_id: Id
    policy_id: Id
    scenario: Id
    as_of: UtcDatetime
    created_at: UtcDatetime
    memory_mode: MemoryMode
    incident_id: Id | None
    flagged: bool
    memory_status: MemoryStatus


# --- Health and errors -----------------------------------------------------


class HealthResponse(Contract):
    status: Annotated[str, Field(pattern=r"^(ok|degraded)$")]
    version: str
    memory_configured: bool
    memory_status: MemoryStatus
    demo_reset_enabled: bool


class ErrorResponse(Contract):
    code: ErrorCode
    message: str
    request_id: str
    details: list[str] = Field(default_factory=list)
