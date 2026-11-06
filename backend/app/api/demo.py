from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.core import orchestration
from app.core.orchestration import Services
from app.core.schemas import (
    DemoLoadRequest,
    DemoLoadResponse,
    DemoResetRequest,
    DemoResetResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])

_ERRORS = {code: {"model": ErrorResponse} for code in (403, 404, 422)}


@router.post("/load", response_model=DemoLoadResponse, responses=_ERRORS)
def load(body: DemoLoadRequest, svc: Services = Depends(get_services)) -> DemoLoadResponse:
    return orchestration.demo_load(svc, body.scenario)


@router.post("/reset", response_model=DemoResetResponse, responses=_ERRORS)
def reset(body: DemoResetRequest, svc: Services = Depends(get_services)) -> DemoResetResponse:
    return orchestration.demo_reset(svc, body.scenario, body.confirm)
