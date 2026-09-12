from dataclasses import dataclass

from app.api.contracts import AccessibilityStatus, Location, RouteStatus, TransportType
from app.services.bus import LowFloorBusRouteMetrics, OdsayBusRouteError, SelectedBusLane
from app.services.calltaxi import TmapRouteError
from app.services.route_orchestration import BackendRecommendationRouteProvider
from app.services.subway import OdsayRouteError, StationAccessibility, SubwayRouteMetrics, SubwayStationKey

ORIGIN = Location(latitude=37.5666, longitude=126.9784)
DESTINATION = Location(latitude=37.4979, longitude=127.0276)


class FakeTmapClient:
    def get_vehicle_route(self, origin: Location, destination: Location) -> tuple[int, int]:
        return 12_500, 1_800


class FakeSubwayClient:
    def get_subway_route(self, origin: Location, destination: Location) -> SubwayRouteMetrics:
        return SubwayRouteMetrics(
            total_time_seconds=2_400,
            total_distance_meters=13_000,
            walking_distance_meters=500,
            walking_time_seconds=480,
            fare_won=1_500,
            station_keys=(SubwayStationKey("2호선", "시청"), SubwayStationKey("2호선", "강남")),
            summary="시청역 → 강남역 지하철 경로",
        )


class FakeAccessibilityProvider:
    def get_station_accessibility(self, station_key: SubwayStationKey) -> StationAccessibility:
        return StationAccessibility(has_operating_elevator=True, elevator_count=1)


class FakeBusClient:
    def get_low_floor_bus_route(self, origin: Location, destination: Location) -> LowFloorBusRouteMetrics:
        return LowFloorBusRouteMetrics(
            total_time_seconds=3_000,
            total_distance_meters=14_000,
            walking_distance_meters=300,
            walking_time_seconds=360,
            fare_won=1_400,
            selected_lanes=(SelectedBusLane("402", "402", "시청", "강남역"),),
            summary="402 저상버스 경로",
        )


class FailingTmapClient:
    def get_vehicle_route(self, origin: Location, destination: Location) -> tuple[int, int]:
        raise TmapRouteError("failed", reason="test_failure")


class FailingSubwayClient:
    def get_subway_route(self, origin: Location, destination: Location) -> SubwayRouteMetrics:
        raise OdsayRouteError("failed", reason="test_failure")


class FailingBusClient:
    def get_low_floor_bus_route(self, origin: Location, destination: Location) -> LowFloorBusRouteMetrics:
        raise OdsayBusRouteError("failed", reason="test_failure")


@dataclass(frozen=True)
class FakeWaitingEstimate:
    expected_minutes: float


def _provider(waiting_time_estimator) -> BackendRecommendationRouteProvider:
    return BackendRecommendationRouteProvider(
        tmap_client=FakeTmapClient(),
        subway_client=FakeSubwayClient(),
        subway_accessibility_provider=FakeAccessibilityProvider(),
        bus_client=FakeBusClient(),
        waiting_time_estimator=waiting_time_estimator,
        current_hour_provider=lambda: 9,
    )


def test_provider_builds_three_backend_owned_routes_and_adds_waiting_time() -> None:
    provider = _provider(lambda hour: FakeWaitingEstimate(expected_minutes=30))

    routes = provider.get_routes(ORIGIN, DESTINATION)

    assert [route.transport_type for route in routes] == list(TransportType)
    calltaxi, subway, bus = routes
    assert calltaxi.total_time_seconds == 30 * 60 + 1_800
    assert calltaxi.walking_distance_meters is None
    assert calltaxi.accessibility_status == AccessibilityStatus.NOT_VERIFIED
    assert any("1800초" in warning for warning in calltaxi.warnings)
    assert subway.accessibility_status == AccessibilityStatus.VERIFIED_AVAILABLE
    assert bus.accessibility_status == AccessibilityStatus.VERIFIED_AVAILABLE


def test_provider_keeps_other_routes_when_waiting_model_is_not_connected() -> None:
    def unavailable_estimator(hour: int) -> object:
        raise NotImplementedError

    routes = _provider(unavailable_estimator).get_routes(ORIGIN, DESTINATION)

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "대기시간 예측 모델" in (routes[0].unavailable_reason or "")
    assert routes[1].status == RouteStatus.AVAILABLE
    assert routes[2].status == RouteStatus.AVAILABLE


def test_provider_rejects_invalid_waiting_prediction_without_fake_value() -> None:
    routes = _provider(lambda hour: FakeWaitingEstimate(expected_minutes=float("nan"))).get_routes(
        ORIGIN, DESTINATION
    )

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "유효하지 않습니다" in (routes[0].unavailable_reason or "")
    assert routes[0].total_time_seconds is None


def test_provider_isolates_each_external_route_failure() -> None:
    def estimate(hour: int) -> FakeWaitingEstimate:
        return FakeWaitingEstimate(expected_minutes=30)

    provider = BackendRecommendationRouteProvider(
        tmap_client=FailingTmapClient(),
        subway_client=FailingSubwayClient(),
        subway_accessibility_provider=FakeAccessibilityProvider(),
        bus_client=FailingBusClient(),
        waiting_time_estimator=estimate,
        current_hour_provider=lambda: 9,
    )

    routes = provider.get_routes(ORIGIN, DESTINATION)

    assert [route.status for route in routes] == [RouteStatus.UNAVAILABLE] * 3
    assert all(route.total_time_seconds is None for route in routes)
