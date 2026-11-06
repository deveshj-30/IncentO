from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.core import orchestration
from app.core.orchestration import Services
from app.core.schemas import PolicySummary

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=list[PolicySummary])
def list_policies(svc: Services = Depends(get_services)) -> list[PolicySummary]:
    return orchestration.list_policies(svc)
