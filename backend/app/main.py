from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import demo, health, investigations, outcomes, policies
from app.api.errors import install_error_handlers
from app.core import modules
from app.core.config import API_VERSION, Settings, get_settings, load_env_into_process
from app.core.database import connect
from app.core.orchestration import Services
from app.core.repository import Repository


def create_app(settings: Settings | None = None, mods: modules.Modules | None = None) -> FastAPI:
    if settings is None:
        # Real startup only: tests and the contract export pass explicit settings and stay hermetic.
        load_env_into_process()
        settings = get_settings()
    app = FastAPI(title="IncentO API", version=API_VERSION)
    app.state.services = Services(
        settings=settings,
        repo=Repository(connect(settings.resolved_database_path)),
        modules=mods or modules.resolve(),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    for router in (health.router, demo.router, policies.router, investigations.router, outcomes.router):
        app.include_router(router)
    return app
