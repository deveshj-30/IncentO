from fastapi import APIRouter, Depends, Response

from app.api.deps import get_services
from app.core import orchestration
from app.core.orchestration import Services
from app.core.schemas import ErrorResponse, Incident, IncidentSummary, Outcome, OutcomeRequest

router = APIRouter(prefix="/api", tags=["incidents"])

_ERRORS = {code: {"model": ErrorResponse} for code in (404, 409, 422)}


@router.get("/incidents", response_model=list[IncidentSummary])
def list_incidents(svc: Services = Depends(get_services)) -> list[IncidentSummary]:
    return svc.repo.list_incidents()


@router.get("/incidents/{incident_id}", response_model=Incident, responses=_ERRORS)
def get_incident(incident_id: str, svc: Services = Depends(get_services)) -> Incident:
    return orchestration.get_incident_or_404(svc, incident_id)


@router.post("/incidents/{incident_id}/outcomes", response_model=Outcome, status_code=201, responses=_ERRORS)
def create_outcome(
    incident_id: str, body: OutcomeRequest, response: Response, svc: Services = Depends(get_services)
) -> Outcome:
    outcome, created = orchestration.create_outcome(svc, incident_id, body)
    response.status_code = 201 if created else 200
    return outcome


@router.post("/outcomes/{outcome_id}/retention", response_model=Outcome, responses=_ERRORS)
def retry_retention(outcome_id: str, svc: Services = Depends(get_services)) -> Outcome:
    return orchestration.retry_retention(svc, outcome_id)
