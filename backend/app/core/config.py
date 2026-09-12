"""애플리케이션 설정 로딩.

환경변수(.env)에서 값을 읽어 Settings 인스턴스 하나로 노출한다.
새 설정값이 필요하면 이 클래스에 필드를 추가하고 backend/.env.example에도 반영한다.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    env: str = "local"
    port: int = 8000
    log_level: str = "INFO"
    enable_sample_routes: bool = False
    tmap_app_key: str | None = Field(default=None, validation_alias=AliasChoices("APP_TMAP_APP_KEY", "TMAP_APP_KEY"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
