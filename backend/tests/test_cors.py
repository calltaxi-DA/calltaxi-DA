from fastapi.testclient import TestClient

from app.main import create_app


def test_local_frontend_origin_can_preflight_recommendation_request() -> None:
    response = TestClient(create_app()).options(
        "/routes/recommendations",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_unknown_frontend_origin_is_not_allowed() -> None:
    response = TestClient(create_app()).options(
        "/routes/recommendations",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers
