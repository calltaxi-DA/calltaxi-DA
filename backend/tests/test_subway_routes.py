from fastapi.testclient import TestClient

from app.api.contracts import AccessibilityStatus, RouteResult, RouteStatus, TransportType
from app.api.subway import get_odsay_subway_route_client, get_subway_accessibility_provider
from app.core.config import get_settings
from app.main import create_app
from app.services.subway import (
    OdsayRouteError,
    StationAccessibility,
    SubwayRouteMetrics,
    SubwayStationKey,
)


class FakeOdsaySubwayRouteClient:
    def get_subway_route(self, origin, destination) -> SubwayRouteMetrics:
        return SubwayRouteMetrics(
            total_time_seconds=2_220,
            total_distance_meters=9_200,
            walking_distance_meters=680,
            walking_time_seconds=660,
            fare_won=1_400,
            station_keys=(
                SubwayStationKey("1호선", "서울"),
                SubwayStationKey("1호선", "시청"),
                SubwayStationKey("2호선", "시청"),
                SubwayStationKey("2호선", "강남"),
            ),
            summary="서울역 → 강남역 지하철 경로",
        )


class FailingOdsaySubwayRouteClient:
    def get_subway_route(self, origin, destination) -> SubwayRouteMetrics:
        raise OdsayRouteError("failed", reason="test_failure")


class FakeAccessibilityProvider:
    def get_station_accessibility(self, station_key: SubwayStationKey) -> StationAccessibility | None:
        if station_key == SubwayStationKey("2호선", "시청"):
            return StationAccessibility(has_operating_elevator=False)
        return StationAccessibility(has_operating_elevator=True, elevator_count=1)


def _route_request_payload() -> dict:
    return {
        "origin": {
            "name": "서울시청",
            "latitude": 37.5666103,
            "longitude": 126.9783882,
            "address": "서울 중구",
        },
        "destination": {
            "name": "강남역",
            "latitude": 37.497952,
            "longitude": 127.027619,
            "address": "서울 강남구",
        },
    }


def test_subway_route_returns_route_result_with_total_walking_distance_and_time() -> None:
    app = create_app()
    app.dependency_overrides[get_odsay_subway_route_client] = lambda: FakeOdsaySubwayRouteClient()
    app.dependency_overrides[get_subway_accessibility_provider] = lambda: FakeAccessibilityProvider()
    client = TestClient(app)

    response = client.post("/routes/subway", json=_route_request_payload())

    assert response.status_code == 200
    route = RouteResult.model_validate(response.json())
    assert route.transport_type == TransportType.SUBWAY
    assert route.status == RouteStatus.AVAILABLE
    assert route.total_time_seconds == 2_220
    assert route.total_distance_meters == 9_200
    assert route.total_cost_won == 1_400
    assert route.walking_distance_meters == 680
    assert route.walking_time_seconds == 660
    assert route.summary == "서울역 → 강남역 지하철 경로"
    assert route.accessibility_status == AccessibilityStatus.VERIFIED_UNAVAILABLE
    assert any("2호선 시청" in warning for warning in route.warnings)
    assert any("총 도보값으로 단정하지 않습니다" in warning for warning in route.warnings)


def test_subway_route_requires_valid_coordinates() -> None:
    app = create_app()
    app.dependency_overrides[get_odsay_subway_route_client] = lambda: FakeOdsaySubwayRouteClient()
    client = TestClient(app)
    payload = _route_request_payload()
    payload["origin"]["longitude"] = 181

    response = client.post("/routes/subway", json=payload)

    assert response.status_code == 422


def test_subway_route_returns_503_without_odsay_key(monkeypatch) -> None:
    monkeypatch.setenv("APP_ODSAY_API_KEY", "")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.post("/routes/subway", json=_route_request_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": "ODsay API key is not configured"}
    get_settings.cache_clear()


def test_subway_route_returns_502_when_odsay_fails() -> None:
    app = create_app()
    app.dependency_overrides[get_odsay_subway_route_client] = lambda: FailingOdsaySubwayRouteClient()
    client = TestClient(app)

    response = client.post("/routes/subway", json=_route_request_payload())

    assert response.status_code == 502
    assert response.json() == {"detail": "Failed to calculate subway route"}
