"""Investigation routes. Slice A: shapes only; behaviour lands in Phase 2 and 3."""

from fastapi import APIRouter, HTTPException

from app.core.schemas import ErrorResponse, Investigation, InvestigationRequest, InvestigationSummary

router = APIRouter(prefix="/api/investigations", tags=["investigations"])

_ERRORS = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    501: {"model": ErrorResponse},
}


@router.post("", response_model=Investigation, status_code=201, responses=_ERRORS)
def create_investigation(request: InvestigationRequest) -> Investigation:
    raise HTTPException(status_code=501, detail="Investigations are not implemented yet (Slice A stub)")


@router.get("", response_model=list[InvestigationSummary], responses=_ERRORS)
def list_investigations() -> list[InvestigationSummary]:
    return []


@router.get("/{run_id}", response_model=Investigation, responses=_ERRORS)
def get_investigation(run_id: str) -> Investigation:
    raise HTTPException(status_code=404, detail=f"No investigation {run_id}")
