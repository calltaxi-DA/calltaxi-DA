import logging

from app.core.logging import configure_logging


def test_configure_logging_suppresses_http_client_request_urls() -> None:
    configure_logging("INFO")

    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING


def test_httpx_info_log_cannot_emit_query_secret(caplog) -> None:
    configure_logging("INFO")
    secret = "regression-test-secret"

    logging.getLogger("httpx").info("GET https://example.test?apiKey=%s", secret)

    assert secret not in caplog.text
