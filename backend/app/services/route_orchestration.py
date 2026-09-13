"""Backend-owned 이동수단 경로 생성과 추천 입력 통합."""

import math
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from ai.waiting_time.estimator import SUPPORTED_MODEL_GROUPS, WaitingTimePredictionError, WaitingTimePredictionInput
from app.api.contracts import (
    AccessibilityStatus,
    Location,
    MetricAvailability,
    RouteMetricAvailability,
    RouteResult,
    RouteStatus,
    TransportType,
)
from app.services.bus import (
    LowFloorBusRouteUnavailableError,
    OdsayBusRouteError,
    OdsayLowFloorBusRouteClient,
)
from app.services.calltaxi import TmapRouteClient, TmapRouteError, calculate_seoul_calltaxi_fare
from app.services.subway import (
    OdsayRouteError,
    OdsaySubwayRouteClient,
    SubwayAccessibilityProvider,
    assess_accessibility_status,
    build_accessibility_warnings,
)
from app.services.waiting_time_features import CONSERVATIVE_MODEL_GROUP_WARNING, WaitingTimeFeatureMappingError

CALLTAXI_WALKING_WARNING = "콜택시 승하차 접근 도보 데이터가 없어 도보 지표를 비교할 수 없습니다."
CALLTAXI_ACCESSIBILITY_WARNING = "이용자 자격과 요청 시점의 실제 배차 가능 여부가 확인되지 않았습니다."
SUBWAY_WALKING_WARNING = (
    "walking_time_seconds와 walking_distance_meters는 ODsay가 제공한 도보 subPath 기준입니다. "
    "지하철 환승 내부 도보시간·거리는 별도 검증 전까지 총 도보값으로 단정하지 않습니다."
)
BUS_ACCESSIBILITY_WARNING = (
    "저상버스 접근성은 노선 단위 보유 정보이며 특정 시간·정류장의 저상버스 도착을 보장하지 않습니다."
)
BUS_WALKING_WARNING = (
    "walking_time_seconds와 walking_distance_meters는 ODsay가 제공한 모든 도보 subPath의 합계이며 "
    "실제 보행로 실측값은 아닙니다."
)


class WaitingTimeEstimateResult(Protocol):
    """AI Adapter 대기시간 결과의 최소 계약."""

    expected_minutes: float
    warnings: tuple[str, ...]

    def to_backend_output(self) -> dict[str, object]:
        """Backend가 소비하는 AI Adapter 출력 계약."""


WaitingTimeInputBuilder = Callable[
    [Location, Location, str, int, datetime],
    tuple[WaitingTimePredictionInput, ...],
]


class BackendRecommendationRouteProvider:
    """Backend service와 AI Adapter 결과만으로 세 이동수단 RouteResult를 생성한다."""

    def __init__(
        self,
        *,
        tmap_client: TmapRouteClient | None,
        subway_client: OdsaySubwayRouteClient | None,
        subway_accessibility_provider: SubwayAccessibilityProvider | None,
        bus_client: OdsayLowFloorBusRouteClient | None,
        waiting_time_estimator: Callable[[WaitingTimePredictionInput], WaitingTimeEstimateResult],
        waiting_time_input_builder: WaitingTimeInputBuilder | None,
        current_time_provider: Callable[[], datetime],
    ) -> None:
        self.tmap_client = tmap_client
        self.subway_client = subway_client
        self.subway_accessibility_provider = subway_accessibility_provider
        self.bus_client = bus_client
        self.waiting_time_estimator = waiting_time_estimator
        self.waiting_time_input_builder = waiting_time_input_builder
        self.current_time_provider = current_time_provider

    def get_routes(
        self,
        origin: Location,
        destination: Location,
        transport_types: list[TransportType],
        calltaxi_purpose: str | None = None,
    ) -> list[RouteResult]:
        route_factories = {
            TransportType.CALLTAXI: self._get_calltaxi_route,
            TransportType.SUBWAY: self._get_subway_route,
            TransportType.LOW_FLOOR_BUS: self._get_bus_route,
        }
        return [
            route_factories[transport_type](origin, destination, calltaxi_purpose)
            if transport_type == TransportType.CALLTAXI
            else route_factories[transport_type](origin, destination)
            for transport_type in transport_types
        ]

    def _get_calltaxi_route(
        self,
        origin: Location,
        destination: Location,
        calltaxi_purpose: str | None,
    ) -> RouteResult:
        if self.tmap_client is None:
            return _unavailable(TransportType.CALLTAXI, "TMAP app key is not configured")
        if calltaxi_purpose is None:
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 이용목적이 없어 대기시간을 예측할 수 없습니다.")
        if self.waiting_time_input_builder is None:
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 대기시간 Prediction feature source가 연결되지 않았습니다.")

        try:
            distance_meters, vehicle_time_seconds = self.tmap_client.get_vehicle_route(origin, destination)
        except TmapRouteError:
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 차량 경로를 계산할 수 없습니다.")

        try:
            prediction_inputs = self.waiting_time_input_builder(
                origin,
                destination,
                calltaxi_purpose,
                distance_meters,
                self.current_time_provider(),
            )
            _validate_prediction_input_groups(prediction_inputs)
            estimate = _select_conservative_waiting_estimate(
                [self.waiting_time_estimator(prediction_input) for prediction_input in prediction_inputs]
            )
            waiting_seconds = _waiting_seconds(estimate)
        except NotImplementedError:
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 대기시간 예측 모델이 연결되지 않았습니다.")
        except WaitingTimeFeatureMappingError as exc:
            return _unavailable(TransportType.CALLTAXI, str(exc))
        except WaitingTimePredictionError:
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 대기시간 예측 모델을 사용할 수 없습니다.")
        except (TypeError, ValueError):
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 대기시간 예측 결과가 유효하지 않습니다.")

        warnings = [
            f"예측 대기시간 {waiting_seconds}초가 총 이동시간에 포함되었습니다.",
            CONSERVATIVE_MODEL_GROUP_WARNING,
            CALLTAXI_WALKING_WARNING,
            CALLTAXI_ACCESSIBILITY_WARNING,
        ]
        warnings.extend(getattr(estimate, "warnings", ()))
        return RouteResult(
            transport_type=TransportType.CALLTAXI,
            status=RouteStatus.AVAILABLE,
            total_time_seconds=waiting_seconds + vehicle_time_seconds,
            total_distance_meters=distance_meters,
            total_cost_won=calculate_seoul_calltaxi_fare(distance_meters),
            predicted_waiting_time_seconds=waiting_seconds,
            vehicle_time_seconds=vehicle_time_seconds,
            walking_distance_meters=None,
            walking_time_seconds=None,
            metric_availability=RouteMetricAvailability(
                walking_distance_meters=MetricAvailability.NOT_AVAILABLE,
                walking_time_seconds=MetricAvailability.NOT_AVAILABLE,
            ),
            accessibility_status=AccessibilityStatus.NOT_VERIFIED,
            summary="장애인 콜택시 경로",
            warnings=warnings,
        )

    def _get_subway_route(self, origin: Location, destination: Location) -> RouteResult:
        if self.subway_client is None:
            return _unavailable(TransportType.SUBWAY, "ODsay API key is not configured")
        try:
            route = self.subway_client.get_subway_route(origin, destination)
        except OdsayRouteError:
            return _unavailable(TransportType.SUBWAY, "지하철 경로를 계산할 수 없습니다.")

        if self.subway_accessibility_provider is None:
            accessibility_status = AccessibilityStatus.NOT_VERIFIED
            warnings = ["지하철역 접근성 lookup을 사용할 수 없어 상세 확인이 필요합니다."]
        else:
            accessibility_status = assess_accessibility_status(
                route.station_keys, self.subway_accessibility_provider
            )
            warnings = build_accessibility_warnings(route.station_keys, self.subway_accessibility_provider)
        warnings.append(SUBWAY_WALKING_WARNING)

        return RouteResult(
            transport_type=TransportType.SUBWAY,
            status=RouteStatus.AVAILABLE,
            total_time_seconds=route.total_time_seconds,
            total_distance_meters=route.total_distance_meters,
            total_cost_won=route.fare_won,
            walking_distance_meters=route.walking_distance_meters,
            walking_time_seconds=route.walking_time_seconds,
            accessibility_status=accessibility_status,
            summary=route.summary,
            route_map_segments=list(route.route_map_segments) or None,
            warnings=warnings,
        )

    def _get_bus_route(self, origin: Location, destination: Location) -> RouteResult:
        if self.bus_client is None:
            return _unavailable(TransportType.LOW_FLOOR_BUS, "ODsay bus route provider is not configured")
        try:
            route = self.bus_client.get_low_floor_bus_route(origin, destination)
        except LowFloorBusRouteUnavailableError:
            return _unavailable(
                TransportType.LOW_FLOOR_BUS,
                "운행 가능한 저상버스 경로를 확인할 수 없습니다.",
                accessibility_status=AccessibilityStatus.VERIFIED_UNAVAILABLE,
            )
        except OdsayBusRouteError:
            return _unavailable(TransportType.LOW_FLOOR_BUS, "저상버스 경로를 계산할 수 없습니다.")

        return RouteResult(
            transport_type=TransportType.LOW_FLOOR_BUS,
            status=RouteStatus.AVAILABLE,
            total_time_seconds=route.total_time_seconds,
            total_distance_meters=route.total_distance_meters,
            total_cost_won=route.fare_won,
            walking_distance_meters=route.walking_distance_meters,
            walking_time_seconds=route.walking_time_seconds,
            accessibility_status=AccessibilityStatus.VERIFIED_AVAILABLE,
            summary=route.summary,
            route_map_segments=list(route.route_map_segments) or None,
            warnings=[BUS_ACCESSIBILITY_WARNING, BUS_WALKING_WARNING],
        )


def _waiting_seconds(estimate: WaitingTimeEstimateResult) -> int:
    backend_output = estimate.to_backend_output()
    if backend_output.get("unit") != "minutes":
        raise ValueError("waiting time estimate unit must be minutes")
    waiting_time = backend_output.get("waitingTime")
    if isinstance(waiting_time, bool) or not isinstance(waiting_time, (int, float)):
        raise TypeError("waiting time estimate waitingTime must be numeric")
    if not math.isfinite(waiting_time) or waiting_time < 0:
        raise ValueError("waiting time estimate must be finite and non-negative")
    return round(waiting_time * 60)


def _select_conservative_waiting_estimate(
    estimates: list[WaitingTimeEstimateResult],
) -> WaitingTimeEstimateResult:
    if not estimates:
        raise ValueError("waiting time estimates must not be empty")
    return max(estimates, key=lambda estimate: _waiting_seconds(estimate))


def _validate_prediction_input_groups(prediction_inputs: tuple[WaitingTimePredictionInput, ...]) -> None:
    expected_groups = set(SUPPORTED_MODEL_GROUPS)
    actual_groups = [prediction_input.model_group for prediction_input in prediction_inputs]
    if len(actual_groups) != len(expected_groups) or set(actual_groups) != expected_groups:
        raise WaitingTimeFeatureMappingError("임차택시_바로콜과 특장차_바로콜을 각각 1회 예측해야 합니다")


def _unavailable(
    transport_type: TransportType,
    reason: str,
    accessibility_status: AccessibilityStatus = AccessibilityStatus.NOT_VERIFIED,
) -> RouteResult:
    return RouteResult(
        transport_type=transport_type,
        status=RouteStatus.UNAVAILABLE,
        accessibility_status=accessibility_status,
        unavailable_reason=reason,
    )
