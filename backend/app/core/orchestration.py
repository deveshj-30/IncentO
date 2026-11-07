"""The only place analysis and memory are connected: analyze, explain and persist a run."""

import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field

from app.core.config import Settings
from app.core.digest import analysis_digest
from app.core.errors import ApiError
from app.core.fixtures import list_scenarios, load_dataset, validate_scenario_name
from app.core.guards import (
    canonical_recalled,
    explanation_codes,
    fallback_explanation,
    require_valid_analysis,
)
from app.core.modules import Modules
from app.core.repository import Repository, now
from app.core.schemas import (
    AnalysisResult,
    DemoLoadResponse,
    DemoResetResponse,
    ErrorCode,
    ExplainContext,
    Explanation,
    Incident,
    Investigation,
    InvestigationRequest,
    MemoryMode,
    MetricStatus,
    Outcome,
    OutcomeRequest,
    PolicySummary,
    RetentionResult,
    RetentionStatus,
    SeedResult,
    SeedStatus,
)

log = logging.getLogger("incento")

DEMO_BANK_PREFIX = "incento-demo-"


@dataclass
class Services:
    settings: Settings
    repo: Repository
    modules: Modules
    executor: ThreadPoolExecutor = field(init=False)

    def __post_init__(self):
        self.executor = ThreadPoolExecutor(
            max_workers=self.settings.module_workers, thread_name_prefix="module"
        )


def call_module(svc: Services, fn, timeout: float, *args):
    """Run a module call with a time limit. A timed-out call keeps running in its worker thread; the
    request stops waiting. Exceptions propagate to the caller, which decides how to degrade."""
    future = svc.executor.submit(fn, *args)
    try:
        return future.result(timeout=timeout)
    except FutureTimeout:
        raise TimeoutError(f"module call exceeded {timeout}s") from None


def incident_id_for(analysis: AnalysisResult) -> str | None:
    """Deterministic ID; None when the data cannot support an incident."""
    if analysis.insufficient_reasons or all(
        m.status == MetricStatus.INSUFFICIENT_DATA for m in analysis.metrics
    ):
        return None
    return f"inc-{analysis.policy_id}-{analysis.comparison_id}"


def _isoz(value) -> str:
    return value.isoformat().replace("+00:00", "Z")


# --- demo ---
def demo_load(svc: Services, scenario: str) -> DemoLoadResponse:
    dataset, checksum = load_dataset(svc.settings.fixtures_dir, scenario)
    existing = svc.repo.get_batch(scenario)
    policies = [p.policy_id for p in dataset.policies]
    if existing and existing["checksum"] == checksum:
        return DemoLoadResponse(
            scenario=scenario,
            checksum=checksum,
            already_loaded=True,
            synthetic=dataset.meta.synthetic,
            policies=policies,
            seed_status=SeedStatus(existing["seed_status"]),
            seed_error=existing["seed_error"],
        )
    seed = _seed(svc, dataset.history, scenario) if dataset.history else None
    status = seed.status if seed else SeedStatus.SKIPPED
    error = seed.error if seed else None
    svc.repo.save_batch(scenario, checksum, status.value, error)
    return DemoLoadResponse(
        scenario=scenario,
        checksum=checksum,
        already_loaded=False,
        synthetic=dataset.meta.synthetic,
        policies=policies,
        seed_status=status,
        seed_error=error,
    )


def _seed(svc: Services, history, scenario: str) -> SeedResult:
    try:
        return call_module(
            svc, svc.modules.seed_history, svc.settings.retain_timeout_seconds, history, scenario
        )
    except Exception as exc:
        log.warning("seed_history failed: %s", type(exc).__name__)
        code = "seed_timeout" if isinstance(exc, TimeoutError) else "seed_error"
        return SeedResult(status=SeedStatus.UNAVAILABLE, error=code)


def demo_reset(svc: Services, scenario: str, confirm: bool) -> DemoResetResponse:
    """Clear a scenario's run state and reset its demo memory bank.

    P2 can only validate the scenario name. The memory adapter (P4) builds the bank name and must itself
    refuse any bank that does not start with ``incento-demo-``.
    """
    if not svc.settings.demo_reset_enabled:
        raise ApiError(403, ErrorCode.FORBIDDEN, "Demo reset is disabled (set DEMO_RESET_ENABLED=true)")
    validate_scenario_name(scenario)
    if not confirm:
        raise ApiError(422, ErrorCode.VALIDATION_ERROR, "confirm must be true")
    with svc.repo.lock:
        try:
            result = call_module(
                svc, svc.modules.reset_demo_bank, svc.settings.retain_timeout_seconds, scenario
            )
        except Exception as exc:
            log.warning("reset_demo_bank failed: %s", type(exc).__name__)
            result = None
        memory_is_stub = "reset_demo_bank" in svc.modules.stubbed
        if result is None or (not result.ok and not memory_is_stub):
            # Clearing SQLite while memory still holds later events would hide them from the as_of guard.
            raise ApiError(
                502,
                ErrorCode.MEMORY_UNAVAILABLE,
                "Memory reset failed; run state was left unchanged",
                [result.error] if result is not None and result.error else [],
            )
        cleared = svc.repo.clear_scenario(scenario)
        seed_status = SeedStatus.SKIPPED
        if result.ok:
            try:
                demo_load(svc, scenario)
                seed_status = SeedStatus(svc.repo.get_batch(scenario)["seed_status"])
            except ApiError:
                seed_status = SeedStatus.UNAVAILABLE
    return DemoResetResponse(
        scenario=scenario, cleared_runs=cleared, memory_reset=result.ok, seed_status=seed_status
    )


def list_policies(svc: Services) -> list[PolicySummary]:
    out = []
    for scenario in list_scenarios(svc.settings.fixtures_dir):
        try:
            dataset, _ = load_dataset(svc.settings.fixtures_dir, scenario)
        except ApiError:
            continue
        out.extend(
            PolicySummary(
                policy_id=p.policy_id,
                version=p.version,
                name=p.name,
                scenario=scenario,
                effective_at=p.effective_at,
                segment=p.segment,
                channel=p.channel,
            )
            for p in dataset.policies
        )
    return out


# --- investigations ---
def create_investigation(svc: Services, request: InvestigationRequest) -> tuple[Investigation, bool]:
    """Return (investigation, created). A repeated key with the same body returns the stored run."""
    with svc.repo.lock:
        prior = svc.repo.find_run_by_key(request.idempotency_key)
        if prior:
            if prior[0] != request:
                raise ApiError(
                    409, ErrorCode.IDEMPOTENCY_CONFLICT, "Idempotency key reused with a different body"
                )
            return prior[1], False

        batch = svc.repo.get_batch(request.scenario)
        if batch is None:
            raise ApiError(
                409,
                ErrorCode.SCENARIO_NOT_LOADED,
                f"Scenario {request.scenario!r} is not loaded; POST /api/demo/load first",
            )
        dataset, checksum = load_dataset(svc.settings.fixtures_dir, request.scenario)
        if checksum != batch["checksum"]:
            raise ApiError(
                409, ErrorCode.SCENARIO_NOT_LOADED, "Fixture changed since load; POST /api/demo/load again"
            )
        if not any(p.policy_id == request.policy_id for p in dataset.policies):
            raise ApiError(
                404, ErrorCode.NOT_FOUND, f"No policy {request.policy_id!r} in {request.scenario!r}"
            )

        analysis = AnalysisResult.model_validate(
            svc.modules.analyze(dataset, request.policy_id, request.as_of)
        )
        require_valid_analysis(analysis, dataset, request.policy_id, request.as_of)
        incident_id = incident_id_for(analysis)

        if request.memory_mode == MemoryMode.LIVE:
            latest = svc.repo.latest_retained_event(request.scenario)
            if latest and request.as_of < latest:
                raise ApiError(
                    409,
                    ErrorCode.AS_OF_BEFORE_MEMORY,
                    "as_of is earlier than the latest retained memory event; "
                    "use memory_mode off or reset the demo",
                    [f"latest_memory_event: {_isoz(latest)}"],
                )
            if incident_id and svc.repo.has_pending_outcome(incident_id):
                raise ApiError(
                    409,
                    ErrorCode.RETENTION_PENDING,
                    "An outcome is still being retained; retry when it is retained",
                )

        run_id = f"run-{svc.repo.next_run_number():04d}-{uuid.uuid4().hex[:6]}"
        context = ExplainContext(
            run_id=run_id,
            scenario=request.scenario,
            policy_id=request.policy_id,
            as_of=request.as_of,
            memory_mode=request.memory_mode,
            incident_id=incident_id,
        )
        explanation = _explain(svc, analysis, context, request, dataset)
        investigation = Investigation(
            run_id=run_id,
            policy_id=request.policy_id,
            scenario=request.scenario,
            as_of=request.as_of,
            created_at=now(),
            memory_mode=request.memory_mode,
            incident_id=incident_id,
            analysis_digest=analysis_digest(analysis),
            synthetic=dataset.meta.synthetic,
            analysis=analysis,
            explanation=explanation,
        )
        svc.repo.save_investigation(request, investigation, analysis.comparison_id)
        return investigation, True


# --- outcomes ---
def create_outcome(svc: Services, incident_id: str, request: OutcomeRequest) -> tuple[Outcome, bool]:
    with svc.repo.lock:
        prior = svc.repo.find_outcome_by_key(request.idempotency_key)
        if prior:
            if prior[0] != request or prior[1].incident_id != incident_id:
                raise ApiError(
                    409, ErrorCode.IDEMPOTENCY_CONFLICT, "Idempotency key reused with a different body"
                )
            return prior[1], False
        incident = svc.repo.get_incident(incident_id)
        if incident is None:
            raise ApiError(404, ErrorCode.NOT_FOUND, f"No incident {incident_id}")
        if request.run_id not in incident.run_ids:
            raise ApiError(422, ErrorCode.VALIDATION_ERROR, "run_id does not belong to this incident")
        outcome = Outcome(
            outcome_id=f"out-{uuid.uuid4().hex[:12]}",
            type=request.type,
            incident_id=incident_id,
            run_id=request.run_id,
            event_time=request.event_time,
            note=_clean_note(request.note),
            idempotency_key=request.idempotency_key,
            retention_status=RetentionStatus.PENDING,
            created_at=now(),
        )
        svc.repo.save_outcome(request, outcome, incident.scenario)
        return _retain(svc, outcome, incident.scenario), True


def retry_retention(svc: Services, outcome_id: str) -> Outcome:
    with svc.repo.lock:
        outcome = svc.repo.get_outcome(outcome_id)
        if outcome is None:
            raise ApiError(404, ErrorCode.NOT_FOUND, f"No outcome {outcome_id}")
        if outcome.retention_status == RetentionStatus.RETAINED:
            return outcome
        incident = get_incident_or_404(svc, outcome.incident_id)
        return _retain(svc, outcome, incident.scenario)


def _explain(
    svc: Services, analysis, context: ExplainContext, request: InvestigationRequest, dataset
) -> Explanation:
    """Call P4's explain; any failure or contract violation degrades to a labeled fallback."""
    try:
        explanation = Explanation.model_validate(
            call_module(svc, svc.modules.explain, svc.settings.explain_timeout_seconds, analysis, context)
        )
    except Exception as exc:
        code = (
            "explain_timeout"
            if isinstance(exc, TimeoutError)
            else "explain_invalid_output"
            if isinstance(exc, ValueError)
            else "explain_failed"
        )
        log.warning("explain failed (%s): %s", context.run_id, code)
        return fallback_explanation([code])
    explanation = canonical_recalled(explanation, dataset)
    codes = explanation_codes(explanation, analysis, request.memory_mode, request.as_of)
    if codes:
        log.warning("explain output rejected (%s): %s", context.run_id, codes)
        return fallback_explanation(codes)
    return explanation


def _retain(svc: Services, outcome: Outcome, scenario: str) -> Outcome:
    try:
        result = RetentionResult.model_validate(
            call_module(
                svc, svc.modules.retain_outcome, svc.settings.retain_timeout_seconds, outcome, scenario
            )
        )
        status, error = result.status, result.error
    except Exception as exc:  # adapter failures must not lose the saved outcome
        log.warning("retain_outcome failed (%s): %s", outcome.outcome_id, type(exc).__name__)
        status = RetentionStatus.FAILED
        error = "retention_timeout" if isinstance(exc, TimeoutError) else "retention_error"
    updated = outcome.model_copy(update={"retention_status": status, "retention_error": error})
    svc.repo.update_retention(updated)
    return updated


_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def _clean_note(note: str) -> str:
    """Strip control characters, URLs and markup; the note is a labeled manager note."""
    cleaned = "".join(ch for ch in note if ch.isprintable())
    cleaned = _URL.sub("", cleaned)
    for ch in "<>`[]":
        cleaned = cleaned.replace(ch, "")
    return " ".join(cleaned.split())


def get_incident_or_404(svc: Services, incident_id: str) -> Incident:
    incident = svc.repo.get_incident(incident_id)
    if incident is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"No incident {incident_id}")
    return incident
