from fastapi.testclient import TestClient

from app.api.bus import get_odsay_low_floor_bus_route_client
from app.api.contracts import RouteResult, RouteStatus, TransportType
from app.core.config import get_settings
from app.main import create_app
from app.services.bus import LowFloorBusRouteMetrics, LowFloorBusRouteUnavailableError, OdsayBusRouteError, SelectedBusLane


class FakeLowFloorBusRouteClient:
    def get_low_floor_bus_route(self, origin, destination) -> LowFloorBusRouteMetrics:
        return LowFloorBusRouteMetrics(
            total_time_seconds=2_520,
            total_distance_meters=11_400,
            walking_distance_meters=780,
            walking_time_seconds=720,
            fare_won=1_500,
            selected_lanes=(
                SelectedBusLane("7016", "7016", "서울역버스환승센터", "광화문"),
                SelectedBusLane("N31", "N31", "광화문", "강남역"),
            ),
            summary="7016 → N31 저상버스 경로",
        )


class UnavailableLowFloorBusRouteClient:
    def get_low_floor_bus_route(self, origin, destination) -> LowFloorBusRouteMetrics:
        raise LowFloorBusRouteUnavailableError("unavailable")


class FailingLowFloorBusRouteClient:
    def get_low_floor_bus_route(self, origin, destination) -> LowFloorBusRouteMetrics:
        raise OdsayBusRouteError("failed", reason="test_failure")


def _route_request_payload() -> dict:
    return {
        "origin": {"name": "서울역", "latitude": 37.5547, "longitude": 126.9706},
        "destination": {"name": "강남역", "latitude": 37.4979, "longitude": 127.0276},
    }


def test_bus_route_returns_low_floor_route_with_total_walking_metrics() -> None:
    app = create_app()
    app.dependency_overrides[get_odsay_low_floor_bus_route_client] = lambda: FakeLowFloorBusRouteClient()
    response = TestClient(app).post("/routes/bus", json=_route_request_payload())

    assert response.status_code == 200
    route = RouteResult.model_validate(response.json())
    assert route.transport_type == TransportType.LOW_FLOOR_BUS
    assert route.status == RouteStatus.AVAILABLE
    assert route.total_time_seconds == 2_520
    assert route.total_distance_meters == 11_400
    assert route.total_cost_won == 1_500
    assert route.walking_distance_meters == 780
    assert route.walking_time_seconds == 720
    assert route.summary == "7016 → N31 저상버스 경로"
    assert any("특정 시간·정류장" in warning for warning in route.warnings)
    assert any("모든 도보 subPath" in warning for warning in route.warnings)


def test_bus_route_returns_unavailable_without_fake_metrics() -> None:
    app = create_app()
    app.dependency_overrides[get_odsay_low_floor_bus_route_client] = lambda: UnavailableLowFloorBusRouteClient()
    response = TestClient(app).post("/routes/bus", json=_route_request_payload())

    assert response.status_code == 200
    route = RouteResult.model_validate(response.json())
    assert route.status == RouteStatus.UNAVAILABLE
    assert route.total_time_seconds is None
    assert route.walking_distance_meters is None
    assert route.unavailable_reason


def test_bus_route_returns_503_without_odsay_key(monkeypatch) -> None:
    monkeypatch.setenv("APP_ODSAY_API_KEY", "")
    monkeypatch.setenv("ODSAY_API_KEY", "")
    get_settings.cache_clear()

    response = TestClient(create_app()).post("/routes/bus", json=_route_request_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": "ODsay API key is not configured"}
    get_settings.cache_clear()


def test_bus_route_returns_502_when_odsay_fails() -> None:
    app = create_app()
    app.dependency_overrides[get_odsay_low_floor_bus_route_client] = lambda: FailingLowFloorBusRouteClient()
    response = TestClient(app).post("/routes/bus", json=_route_request_payload())

    assert response.status_code == 502
    assert response.json() == {"detail": "Failed to calculate low-floor bus route"}


def test_bus_route_requires_valid_coordinates() -> None:
    app = create_app()
    app.dependency_overrides[get_odsay_low_floor_bus_route_client] = lambda: FakeLowFloorBusRouteClient()
    payload = _route_request_payload()
    payload["destination"]["latitude"] = 91

    response = TestClient(app).post("/routes/bus", json=payload)

    assert response.status_code == 422
