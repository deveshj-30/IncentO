from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, investigations
from app.api.errors import install_error_handlers
from app.core.config import API_VERSION, get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="IncentiveTrap API", version=API_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(investigations.router)
    return app


app = create_app()
