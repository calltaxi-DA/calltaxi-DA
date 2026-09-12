import logging

from app.core.logging import configure_logging


def test_configure_logging_suppresses_http_client_request_urls() -> None:
    configure_logging("INFO")

    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING
