from fastapi import Request

from app.core.orchestration import Services


def get_services(request: Request) -> Services:
    return request.app.state.services
