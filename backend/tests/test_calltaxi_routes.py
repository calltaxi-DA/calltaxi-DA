from fastapi.testclient import TestClient
import httpx

from app.api.calltaxi import get_tmap_route_client
from app.api.contracts import CalltaxiRouteResponse, TransportType
from app.core.config import get_settings
from app.main import create_app
from app.services.calltaxi import TmapRouteClient, TmapRouteError


class FakeTmapRouteClient:
    def __init__(self, distance_meters: int = 12_500, time_seconds: int = 1_800) -> None:
        self.distance_meters = distance_meters
        self.time_seconds = time_seconds

    def get_vehicle_route(self, origin, destination) -> tuple[int, int]:
        return self.distance_meters, self.time_seconds


class FailingTmapRouteClient:
    def get_vehicle_route(self, origin, destination) -> tuple[int, int]:
        raise TmapRouteError("failed", reason="test_failure")


def _route_request_payload() -> dict:
    return {
        "origin": {
            "name": "서울시청",
            "latitude": 37.5666103,
            "longitude": 126.9783882,
            "address": "서울 중구",
        },
        "destination": {
            "name": "서울역",
            "latitude": 37.5546788,
            "longitude": 126.9706069,
            "address": "서울 용산구",
        },
    }


def test_calltaxi_route_returns_vehicle_distance_time_and_fare() -> None:
    app = create_app()
    app.dependency_overrides[get_tmap_route_client] = lambda: FakeTmapRouteClient()
    client = TestClient(app)

    response = client.post("/routes/calltaxi", json=_route_request_payload())

    assert response.status_code == 200
    route = CalltaxiRouteResponse.model_validate(response.json())
    assert route.transport_type == TransportType.CALLTAXI
    assert route.vehicle_distance_meters == 12_500
    assert route.vehicle_time_seconds == 1_800
    assert route.estimated_fare_won == 3_000
    assert "통행료·주차료" in route.warnings[0]
    assert "total_time_seconds" not in response.json()


def test_calltaxi_route_requires_valid_coordinates() -> None:
    app = create_app()
    app.dependency_overrides[get_tmap_route_client] = lambda: FakeTmapRouteClient()
    client = TestClient(app)
    payload = _route_request_payload()
    payload["origin"]["latitude"] = 91

    response = client.post("/routes/calltaxi", json=payload)

    assert response.status_code == 422


def test_calltaxi_route_returns_503_without_tmap_key(monkeypatch) -> None:
    monkeypatch.setenv("APP_TMAP_APP_KEY", "")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.post("/routes/calltaxi", json=_route_request_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": "TMAP app key is not configured"}
    get_settings.cache_clear()


def test_calltaxi_route_returns_502_when_tmap_fails() -> None:
    app = create_app()
    app.dependency_overrides[get_tmap_route_client] = lambda: FailingTmapRouteClient()
    client = TestClient(app)

    response = client.post("/routes/calltaxi", json=_route_request_payload())

    assert response.status_code == 502
    assert response.json() == {"detail": "Failed to calculate calltaxi vehicle route"}


def test_calltaxi_route_returns_502_when_tmap_returns_invalid_json() -> None:
    app = create_app()
    invalid_json_client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html>error</html>"))
    )
    app.dependency_overrides[get_tmap_route_client] = lambda: TmapRouteClient(
        app_key="test-app-key",
        http_client=invalid_json_client,
    )
    client = TestClient(app)

    response = client.post("/routes/calltaxi", json=_route_request_payload())

    assert response.status_code == 502
    assert response.json() == {"detail": "Failed to calculate calltaxi vehicle route"}
