"""애플리케이션 공통 예외 처리."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.exceptions")


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """예상하지 못한 서버 예외를 안전한 500 응답으로 변환한다."""

    logger.exception("unhandled_exception path=%s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
