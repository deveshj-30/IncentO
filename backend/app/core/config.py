"""Environment loading. Secrets stay server-side and are never logged or returned."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

API_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Variable names are proposals until P4 confirms the Hindsight client settings.
    hindsight_api_key: SecretStr | None = None
    hindsight_base_url: str | None = None
    demo_reset_enabled: bool = False
    database_path: str = ".local/incento.sqlite3"
    cors_origins: str = "http://localhost:5173"
    explain_timeout_seconds: float = Field(default=60.0, gt=0)
    retain_timeout_seconds: float = Field(default=30.0, gt=0)
    module_workers: int = Field(default=8, ge=1, le=64)
    fixtures_dir: str = str(REPO_ROOT / "data" / "scenarios")

    @property
    def resolved_database_path(self) -> str:
        """Relative paths resolve against the repository root, not the working directory."""
        if self.database_path == ":memory:" or Path(self.database_path).is_absolute():
            return self.database_path
        return str(REPO_ROOT / self.database_path)

    @property
    def memory_configured(self) -> bool:
        return self.hindsight_api_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
