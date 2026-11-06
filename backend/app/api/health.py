from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.core.config import API_VERSION
from app.core.orchestration import Services
from app.core.schemas import HealthResponse, MemoryStatus

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(svc: Services = Depends(get_services)) -> HealthResponse:
    settings = svc.settings
    # Real memory probing arrives with P4's adapter; until then report configuration only.
    return HealthResponse(
        status="ok",
        version=API_VERSION,
        memory_configured=settings.memory_configured,
        memory_status=MemoryStatus.UNAVAILABLE,
        demo_reset_enabled=settings.demo_reset_enabled,
        stubbed_modules=svc.modules.stubbed,
    )
