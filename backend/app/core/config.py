"""Environment loading. Secrets stay server-side and are never logged or returned."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

API_VERSION = "0.1.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Variable names are proposals until P4 confirms the Hindsight client settings.
    hindsight_api_key: SecretStr | None = None
    hindsight_base_url: str | None = None
    demo_reset_enabled: bool = False
    database_path: str = ".local/incento.sqlite3"
    cors_origins: str = "http://localhost:5173"
    fixtures_dir: str = str(Path(__file__).resolve().parents[3] / "data" / "scenarios")

    @property
    def memory_configured(self) -> bool:
        return self.hindsight_api_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
