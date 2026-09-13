from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from ai.waiting_time.estimator import (
    WAITING_TIME_UNIT,
    WaitingTimePredictionAdapter,
    WaitingTimePredictionError,
    WaitingTimePredictionInput,
)
from app.api.contracts import (
    AccessibilityStatus,
    Location,
    RouteMapPoint,
    RouteMapSegment,
    RouteMapSegmentType,
    RouteStatus,
    TransportType,
)
from app.services.bus import LowFloorBusRouteMetrics, OdsayBusRouteError, SelectedBusLane
from app.services.calltaxi import TmapRouteError
from app.services.route_orchestration import BackendRecommendationRouteProvider
from app.services.subway import OdsayRouteError, StationAccessibility, SubwayRouteMetrics, SubwayStationKey
from app.services.waiting_time_features import WaitingTimeFeatureMappingError
from app.services.waiting_time_features import (
    ConfiguredWaitingTimeInputBuilder,
    JsonVehicleOperationCountProvider,
    JsonWeatherObservationProvider,
)

ORIGIN = Location(latitude=37.5666, longitude=126.9784)
DESTINATION = Location(latitude=37.4979, longitude=127.0276)
REQUESTED_AT = datetime(2026, 9, 13, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))


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
            route_map_segments=(
                RouteMapSegment(
                    segment_type=RouteMapSegmentType.SUBWAY,
                    label="2호선",
                    points=[
                        RouteMapPoint(latitude=37.565715, longitude=126.977108, name="시청"),
                        RouteMapPoint(latitude=37.497942, longitude=127.027621, name="강남"),
                    ],
                ),
            ),
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
            route_map_segments=(
                RouteMapSegment(
                    segment_type=RouteMapSegmentType.BUS,
                    label="402",
                    points=[
                        RouteMapPoint(latitude=37.565715, longitude=126.977108, name="시청"),
                        RouteMapPoint(latitude=37.497942, longitude=127.027621, name="강남역"),
                    ],
                ),
            ),
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
    warnings: tuple[str, ...] = ()
    unit: str = WAITING_TIME_UNIT

    def to_backend_output(self) -> dict[str, object]:
        return {
            "waitingTime": self.expected_minutes,
            "unit": self.unit,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class InvalidWaitingEstimate:
    expected_minutes: object
    warnings: tuple[str, ...] = ()
    unit: str = WAITING_TIME_UNIT

    def to_backend_output(self) -> dict[str, object]:
        return {
            "waitingTime": self.expected_minutes,
            "unit": self.unit,
            "warnings": self.warnings,
        }


def _prediction_input(model_group: str, ride_distance_meters: float = 12_500) -> WaitingTimePredictionInput:
    return WaitingTimePredictionInput(
        requested_at=REQUESTED_AT,
        purpose="치료",
        ride_distance_meters=ride_distance_meters,
        origin_gu="중구",
        origin_dong="명동",
        destination_gu="강남구",
        destination_dong="역삼동",
        movement_type="구 간 이동",
        model_group=model_group,
        vehicle_operation_count_prev_day=412,
        temperature_c=23.5,
        precipitation_mm=0,
        wind_speed_ms=2,
        snow_depth_cm=0,
        is_bad_weather=False,
    )


def _input_builder(
    origin: Location,
    destination: Location,
    purpose: str,
    ride_distance_meters: int,
    requested_at: datetime,
) -> tuple[WaitingTimePredictionInput, ...]:
    assert purpose == "치료"
    assert ride_distance_meters == 12_500
    assert requested_at == REQUESTED_AT
    return (
        _prediction_input("임차택시_바로콜", ride_distance_meters),
        _prediction_input("특장차_바로콜", ride_distance_meters),
    )


def _provider(
    waiting_time_estimator,
    *,
    waiting_time_input_builder=_input_builder,
) -> BackendRecommendationRouteProvider:
    return BackendRecommendationRouteProvider(
        tmap_client=FakeTmapClient(),
        subway_client=FakeSubwayClient(),
        subway_accessibility_provider=FakeAccessibilityProvider(),
        bus_client=FakeBusClient(),
        waiting_time_estimator=waiting_time_estimator,
        waiting_time_input_builder=waiting_time_input_builder,
        current_time_provider=lambda: REQUESTED_AT,
    )


def test_provider_builds_three_backend_owned_routes_and_adds_conservative_waiting_time() -> None:
    seen_groups: list[str] = []

    def estimate(prediction_input: WaitingTimePredictionInput) -> FakeWaitingEstimate:
        seen_groups.append(prediction_input.model_group)
        if prediction_input.model_group == "임차택시_바로콜":
            return FakeWaitingEstimate(expected_minutes=20)
        return FakeWaitingEstimate(expected_minutes=30, warnings=("out_of_training_target_range",))

    provider = _provider(estimate)

    routes = provider.get_routes(ORIGIN, DESTINATION, list(TransportType), calltaxi_purpose="치료")

    assert [route.transport_type for route in routes] == list(TransportType)
    calltaxi, subway, bus = routes
    assert seen_groups == ["임차택시_바로콜", "특장차_바로콜"]
    assert calltaxi.predicted_waiting_time_seconds == 30 * 60
    assert calltaxi.vehicle_time_seconds == 1_800
    assert calltaxi.total_time_seconds == 30 * 60 + 1_800
    assert calltaxi.total_distance_meters == 12_500
    assert calltaxi.total_cost_won == 3_000
    assert calltaxi.walking_distance_meters is None
    assert calltaxi.accessibility_status == AccessibilityStatus.NOT_VERIFIED
    assert any("1800초" in warning for warning in calltaxi.warnings)
    assert any("임차택시/특장차" in warning for warning in calltaxi.warnings)
    assert "out_of_training_target_range" in calltaxi.warnings
    assert subway.accessibility_status == AccessibilityStatus.VERIFIED_AVAILABLE
    assert subway.route_map_segments is not None
    assert subway.route_map_segments[0].segment_type == RouteMapSegmentType.SUBWAY
    assert bus.accessibility_status == AccessibilityStatus.VERIFIED_AVAILABLE
    assert bus.route_map_segments is not None
    assert bus.route_map_segments[0].label == "402"


def test_provider_uses_waiting_time_backend_output_contract_for_total_time() -> None:
    provider = _provider(lambda prediction_input: FakeWaitingEstimate(expected_minutes=12.5))

    route = provider.get_routes(ORIGIN, DESTINATION, [TransportType.CALLTAXI], calltaxi_purpose="치료")[0]

    assert route.predicted_waiting_time_seconds == round(12.5 * 60)
    assert route.vehicle_time_seconds == 1_800
    assert route.total_time_seconds == route.predicted_waiting_time_seconds + route.vehicle_time_seconds


def test_provider_uses_configured_feature_builder_and_prediction_adapter_contract(tmp_path: Path) -> None:
    operation_lookup = tmp_path / "operation-count.json"
    weather_lookup = tmp_path / "weather.json"
    operation_lookup.write_text('{"2026-09-12": 412}', encoding="utf-8")
    weather_lookup.write_text(
        '{"2026-09-13T09:00:00+09:00": {'
        '"temperature_c": 23.5, "precipitation_mm": 0, "wind_speed_ms": 2.1, '
        '"snow_depth_cm": 0, "new_snow_3h_cm": 0'
        "}}",
        encoding="utf-8",
    )
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib placeholder")
    seen_groups: list[str] = []

    class FakePredictionModel:
        def predict(self, model_input) -> list[float]:
            model_group = model_input.iloc[0]["model_group"]
            seen_groups.append(model_group)
            if model_group == "임차택시_바로콜":
                return [18.0]
            return [32.0]

    adapter = WaitingTimePredictionAdapter(
        model_path=model_path,
        model_name="test_rf_model",
        model_loader=lambda path: FakePredictionModel(),
    )
    builder = ConfiguredWaitingTimeInputBuilder(
        operation_count_provider=JsonVehicleOperationCountProvider(operation_lookup),
        weather_provider=JsonWeatherObservationProvider(weather_lookup),
    )
    provider = BackendRecommendationRouteProvider(
        tmap_client=FakeTmapClient(),
        subway_client=None,
        subway_accessibility_provider=None,
        bus_client=None,
        waiting_time_estimator=adapter.estimate,
        waiting_time_input_builder=builder,
        current_time_provider=lambda: datetime(2026, 9, 13, 0, 15, tzinfo=ZoneInfo("UTC")),
    )

    route = provider.get_routes(
        Location(latitude=37.5666, longitude=126.9784, address="서울특별시 중구 명동"),
        Location(latitude=37.4979, longitude=127.0276, address="서울특별시 강남구 역삼동"),
        [TransportType.CALLTAXI],
        calltaxi_purpose="치료",
    )[0]

    assert seen_groups == ["임차택시_바로콜", "특장차_바로콜"]
    assert route.predicted_waiting_time_seconds == 32 * 60
    assert route.vehicle_time_seconds == 1_800
    assert route.total_time_seconds == 32 * 60 + 1_800
    assert route.total_distance_meters == 12_500
    assert route.total_cost_won == 3_000


def test_provider_keeps_other_routes_when_waiting_model_is_not_connected() -> None:
    def unavailable_estimator(prediction_input: WaitingTimePredictionInput) -> object:
        raise NotImplementedError

    routes = _provider(unavailable_estimator).get_routes(
        ORIGIN, DESTINATION, list(TransportType), calltaxi_purpose="치료"
    )

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "대기시간 예측 모델" in (routes[0].unavailable_reason or "")
    assert routes[1].status == RouteStatus.AVAILABLE
    assert routes[2].status == RouteStatus.AVAILABLE


def test_provider_rejects_invalid_waiting_prediction_without_fake_value() -> None:
    routes = _provider(lambda prediction_input: FakeWaitingEstimate(expected_minutes=float("nan"))).get_routes(
        ORIGIN, DESTINATION, list(TransportType), calltaxi_purpose="치료"
    )

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "유효하지 않습니다" in (routes[0].unavailable_reason or "")
    assert routes[0].total_time_seconds is None


def test_provider_returns_unavailable_without_fake_value_when_feature_mapping_fails() -> None:
    def missing_feature_builder(
        origin: Location,
        destination: Location,
        purpose: str,
        ride_distance_meters: int,
        requested_at: datetime,
    ) -> tuple[WaitingTimePredictionInput, ...]:
        raise WaitingTimeFeatureMappingError("weather lookup 값이 없습니다")

    routes = _provider(
        lambda prediction_input: FakeWaitingEstimate(expected_minutes=30),
        waiting_time_input_builder=missing_feature_builder,
    ).get_routes(ORIGIN, DESTINATION, list(TransportType), calltaxi_purpose="치료")

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert routes[0].unavailable_reason == "weather lookup 값이 없습니다"
    assert routes[0].total_time_seconds is None
    assert routes[0].metric_availability is not None
    assert all(value == "not_available" for value in routes[0].metric_availability.model_dump().values())
    assert routes[1].status == RouteStatus.AVAILABLE
    assert routes[2].status == RouteStatus.AVAILABLE


def test_provider_returns_unavailable_without_fake_value_when_prediction_call_fails() -> None:
    def failing_estimator(prediction_input: WaitingTimePredictionInput) -> FakeWaitingEstimate:
        raise WaitingTimePredictionError("model predict failed")

    routes = _provider(failing_estimator).get_routes(
        ORIGIN, DESTINATION, list(TransportType), calltaxi_purpose="치료"
    )

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "모델을 사용할 수 없습니다" in (routes[0].unavailable_reason or "")
    assert routes[0].total_time_seconds is None
    assert routes[0].total_distance_meters is None
    assert routes[0].total_cost_won is None
    assert routes[1].status == RouteStatus.AVAILABLE
    assert routes[2].status == RouteStatus.AVAILABLE


@pytest.mark.parametrize("invalid_minutes", [None, float("inf"), "30"])
def test_provider_rejects_invalid_typed_waiting_prediction_without_fake_value(
    invalid_minutes: object,
) -> None:
    routes = _provider(lambda prediction_input: InvalidWaitingEstimate(expected_minutes=invalid_minutes)).get_routes(
        ORIGIN, DESTINATION, [TransportType.CALLTAXI], calltaxi_purpose="치료"
    )

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "유효하지 않습니다" in (routes[0].unavailable_reason or "")
    assert routes[0].total_time_seconds is None


def test_provider_rejects_negative_waiting_prediction_without_adding_vehicle_time() -> None:
    routes = _provider(lambda prediction_input: FakeWaitingEstimate(expected_minutes=-1)).get_routes(
        ORIGIN, DESTINATION, [TransportType.CALLTAXI], calltaxi_purpose="치료"
    )

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert routes[0].total_time_seconds is None


def test_provider_rejects_non_minutes_waiting_time_unit_without_total_time() -> None:
    routes = _provider(lambda prediction_input: FakeWaitingEstimate(expected_minutes=30, unit="seconds")).get_routes(
        ORIGIN, DESTINATION, [TransportType.CALLTAXI], calltaxi_purpose="치료"
    )

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert routes[0].total_time_seconds is None
    assert routes[0].predicted_waiting_time_seconds is None
    assert routes[0].vehicle_time_seconds is None


def test_provider_rejects_partial_model_group_prediction_failure_without_fallback_to_success() -> None:
    seen_groups: list[str] = []

    def estimate(prediction_input: WaitingTimePredictionInput) -> FakeWaitingEstimate:
        seen_groups.append(prediction_input.model_group)
        if prediction_input.model_group == "특장차_바로콜":
            raise WaitingTimePredictionError("second model group failed")
        return FakeWaitingEstimate(expected_minutes=20)

    routes = _provider(estimate).get_routes(
        ORIGIN, DESTINATION, [TransportType.CALLTAXI], calltaxi_purpose="치료"
    )

    assert seen_groups == ["임차택시_바로콜", "특장차_바로콜"]
    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert routes[0].total_time_seconds is None


def test_provider_isolates_each_external_route_failure() -> None:
    def estimate(prediction_input: WaitingTimePredictionInput) -> FakeWaitingEstimate:
        return FakeWaitingEstimate(expected_minutes=30)

    provider = BackendRecommendationRouteProvider(
        tmap_client=FailingTmapClient(),
        subway_client=FailingSubwayClient(),
        subway_accessibility_provider=FakeAccessibilityProvider(),
        bus_client=FailingBusClient(),
        waiting_time_estimator=estimate,
        waiting_time_input_builder=_input_builder,
        current_time_provider=lambda: REQUESTED_AT,
    )

    routes = provider.get_routes(ORIGIN, DESTINATION, list(TransportType), calltaxi_purpose="치료")

    assert [route.status for route in routes] == [RouteStatus.UNAVAILABLE] * 3
    assert all(route.total_time_seconds is None for route in routes)


def test_provider_only_calls_selected_transport_services() -> None:
    provider = _provider(lambda prediction_input: FakeWaitingEstimate(expected_minutes=30))

    routes = provider.get_routes(ORIGIN, DESTINATION, [TransportType.SUBWAY])

    assert [route.transport_type for route in routes] == [TransportType.SUBWAY]


def test_provider_returns_calltaxi_unavailable_when_purpose_is_missing() -> None:
    provider = _provider(lambda prediction_input: FakeWaitingEstimate(expected_minutes=30))

    routes = provider.get_routes(ORIGIN, DESTINATION, [TransportType.CALLTAXI])

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "이용목적" in (routes[0].unavailable_reason or "")


def test_provider_returns_calltaxi_unavailable_when_feature_source_is_not_connected() -> None:
    provider = _provider(
        lambda prediction_input: FakeWaitingEstimate(expected_minutes=30),
        waiting_time_input_builder=None,
    )

    routes = provider.get_routes(ORIGIN, DESTINATION, [TransportType.CALLTAXI], calltaxi_purpose="치료")

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "feature source" in (routes[0].unavailable_reason or "")


def test_provider_requires_both_calltaxi_model_groups_before_prediction() -> None:
    seen_inputs: list[WaitingTimePredictionInput] = []

    def one_group_builder(
        origin: Location,
        destination: Location,
        purpose: str,
        ride_distance_meters: int,
        requested_at: datetime,
    ) -> tuple[WaitingTimePredictionInput, ...]:
        return (_prediction_input("특장차_바로콜", ride_distance_meters),)

    def estimate(prediction_input: WaitingTimePredictionInput) -> FakeWaitingEstimate:
        seen_inputs.append(prediction_input)
        return FakeWaitingEstimate(expected_minutes=30)

    provider = _provider(estimate, waiting_time_input_builder=one_group_builder)

    routes = provider.get_routes(ORIGIN, DESTINATION, [TransportType.CALLTAXI], calltaxi_purpose="치료")

    assert routes[0].status == RouteStatus.UNAVAILABLE
    assert "각각 1회" in (routes[0].unavailable_reason or "")
    assert seen_inputs == []
