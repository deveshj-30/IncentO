from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.core.config import API_VERSION
from app.core.orchestration import Services
from app.core.schemas import HealthResponse, MemoryStatus

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(svc: Services = Depends(get_services)) -> HealthResponse:
    settings = svc.settings
    # Reports how memory is configured (a key means `live`, simulation means `fixture`); it does not
    # call the memory service, so it says nothing about whether Hindsight is reachable right now.
    return HealthResponse(
        status="ok",
        version=API_VERSION,
        memory_configured=settings.memory_configured,
        memory_status=_memory_status(svc),
        demo_reset_enabled=settings.demo_reset_enabled,
        stubbed_modules=svc.modules.stubbed,
    )


def _memory_status(svc: Services) -> MemoryStatus:
    probe = svc.modules.memory_status
    if probe is None:
        return MemoryStatus.UNAVAILABLE
    try:
        return MemoryStatus(probe())
    except Exception:  # health must never fail because of memory
        return MemoryStatus.UNAVAILABLE
