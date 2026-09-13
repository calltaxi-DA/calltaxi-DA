"""애플리케이션 설정 로딩.

저장소 루트 `.env`에서 값을 읽어 Settings 인스턴스 하나로 노출한다.
새 설정값이 필요하면 이 클래스에 필드를 추가하고 루트 `.env.example`에도 반영한다.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_PATH, env_prefix="APP_", extra="ignore")

    env: str = "local"
    port: int = 8000
    log_level: str = "INFO"
    enable_sample_routes: bool = False
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    tmap_app_key: str | None = Field(default=None, validation_alias=AliasChoices("APP_TMAP_APP_KEY", "TMAP_APP_KEY"))
    odsay_api_key: str | None = Field(default=None, validation_alias=AliasChoices("APP_ODSAY_API_KEY", "ODSAY_API_KEY"))
    transport_cost_db_path: Path = Path("backend/var/transport_costs.sqlite3")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def resolved_transport_cost_db_path(self) -> Path:
        if self.transport_cost_db_path.is_absolute():
            return self.transport_cost_db_path
        return ROOT_ENV_PATH.parent / self.transport_cost_db_path


@lru_cache
def get_settings() -> Settings:
    return Settings()
