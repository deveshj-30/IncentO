from fastapi import APIRouter

from app.core.config import API_VERSION, get_settings
from app.core.schemas import HealthResponse, MemoryStatus

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    # Real memory probing arrives with P4's adapter; until then report configuration only.
    return HealthResponse(
        status="ok",
        version=API_VERSION,
        memory_configured=settings.memory_configured,
        memory_status=MemoryStatus.UNAVAILABLE,
        demo_reset_enabled=settings.demo_reset_enabled,
    )
