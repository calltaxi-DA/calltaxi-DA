"""FastAPI 애플리케이션 진입점.

로컬 실행: uvicorn app.main:app --reload --port 8000 (backend/ 디렉터리에서)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import internal_server_error_handler
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("app_startup env=%s port=%s", settings.env, settings.port)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="calltaxi-service", version="0.1.0", lifespan=lifespan)
    app.add_exception_handler(Exception, internal_server_error_handler)
    app.include_router(health_router)
    return app


app = create_app()
