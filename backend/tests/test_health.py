from fastapi.testclient import TestClient

from app.main import app, create_app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unhandled_exception_returns_safe_500_response() -> None:
    test_app = create_app()

    @test_app.get("/raise-error")
    def raise_error() -> None:
        raise RuntimeError("sensitive detail")

    error_client = TestClient(test_app, raise_server_exceptions=False)

    response = error_client.get("/raise-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
