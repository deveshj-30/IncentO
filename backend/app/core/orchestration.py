"""The only place analysis and memory are connected: analyze, explain and persist a run."""

import uuid
from dataclasses import dataclass

from app.core.config import Settings
from app.core.digest import analysis_digest
from app.core.errors import ApiError
from app.core.fixtures import list_scenarios, load_dataset
from app.core.modules import Modules
from app.core.repository import Repository, now
from app.core.schemas import (
    AnalysisResult,
    DemoLoadResponse,
    DemoResetResponse,
    ErrorCode,
    ExplainContext,
    Incident,
    Investigation,
    InvestigationRequest,
    MemoryMode,
    MetricStatus,
    Outcome,
    OutcomeRequest,
    PolicySummary,
    RetentionStatus,
    SeedStatus,
)

DEMO_BANK_PREFIX = "incento-demo-"


@dataclass
class Services:
    settings: Settings
    repo: Repository
    modules: Modules


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
    seed = svc.modules.seed_history(dataset.history) if dataset.history else None
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


def demo_reset(svc: Services, scenario: str, confirm: bool) -> DemoResetResponse:
    if not svc.settings.demo_reset_enabled:
        raise ApiError(403, ErrorCode.FORBIDDEN, "Demo reset is disabled (set DEMO_RESET_ENABLED=true)")
    if not confirm:
        raise ApiError(422, ErrorCode.VALIDATION_ERROR, "confirm must be true")
    # P4 owns bank naming; P2 enforces the prefix guard before anything is deleted.
    bank = f"{DEMO_BANK_PREFIX}{scenario}"
    if not bank.startswith(DEMO_BANK_PREFIX):
        raise ApiError(403, ErrorCode.FORBIDDEN, "Refusing to reset a non-demo bank")
    result = svc.modules.reset_demo_bank(scenario)
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

        analysis = svc.modules.analyze(dataset, request.policy_id, request.as_of)
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
        explanation = svc.modules.explain(analysis, context)
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
        return _retain(svc, outcome), True


def retry_retention(svc: Services, outcome_id: str) -> Outcome:
    with svc.repo.lock:
        outcome = svc.repo.get_outcome(outcome_id)
        if outcome is None:
            raise ApiError(404, ErrorCode.NOT_FOUND, f"No outcome {outcome_id}")
        if outcome.retention_status == RetentionStatus.RETAINED:
            return outcome
        return _retain(svc, outcome)


def _retain(svc: Services, outcome: Outcome) -> Outcome:
    try:
        result = svc.modules.retain_outcome(outcome)
        status, error = result.status, result.error
    except Exception:  # adapter failures must not lose the saved outcome
        status, error = RetentionStatus.FAILED, "retention_error"
    updated = outcome.model_copy(update={"retention_status": status, "retention_error": error})
    svc.repo.update_retention(updated)
    return updated


def _clean_note(note: str) -> str:
    """Strip control characters, markup and angle brackets; the note is a labeled manager note."""
    cleaned = "".join(ch for ch in note if ch.isprintable() or ch == " ")
    for ch in "<>`":
        cleaned = cleaned.replace(ch, "")
    return cleaned.strip()


def get_incident_or_404(svc: Services, incident_id: str) -> Incident:
    incident = svc.repo.get_incident(incident_id)
    if incident is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"No incident {incident_id}")
    return incident
