from fastapi import APIRouter, Depends, Response

from app.api.deps import get_services
from app.core import orchestration
from app.core.errors import ApiError
from app.core.orchestration import Services
from app.core.schemas import (
    ErrorCode,
    ErrorResponse,
    Investigation,
    InvestigationRequest,
    InvestigationSummary,
)

router = APIRouter(prefix="/api/investigations", tags=["investigations"])

_ERRORS = {code: {"model": ErrorResponse} for code in (403, 404, 409, 422)}


@router.post("", response_model=Investigation, status_code=201, responses=_ERRORS)
def create_investigation(
    request: InvestigationRequest, response: Response, svc: Services = Depends(get_services)
) -> Investigation:
    investigation, created = orchestration.create_investigation(svc, request)
    response.status_code = 201 if created else 200
    return investigation


@router.get("", response_model=list[InvestigationSummary], responses=_ERRORS)
def list_investigations(svc: Services = Depends(get_services)) -> list[InvestigationSummary]:
    return svc.repo.list_investigations()


@router.get("/{run_id}", response_model=Investigation, responses=_ERRORS)
def get_investigation(run_id: str, svc: Services = Depends(get_services)) -> Investigation:
    investigation = svc.repo.get_investigation(run_id)
    if investigation is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"No investigation {run_id}")
    return investigation
