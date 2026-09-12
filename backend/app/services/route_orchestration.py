"""Backend-owned 이동수단 경로 생성과 추천 입력 통합."""

import math
from collections.abc import Callable
from typing import Protocol

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


class BackendRecommendationRouteProvider:
    """Backend service와 AI Adapter 결과만으로 세 이동수단 RouteResult를 생성한다."""

    def __init__(
        self,
        *,
        tmap_client: TmapRouteClient | None,
        subway_client: OdsaySubwayRouteClient | None,
        subway_accessibility_provider: SubwayAccessibilityProvider | None,
        bus_client: OdsayLowFloorBusRouteClient | None,
        waiting_time_estimator: Callable[[int], WaitingTimeEstimateResult],
        current_hour_provider: Callable[[], int],
    ) -> None:
        self.tmap_client = tmap_client
        self.subway_client = subway_client
        self.subway_accessibility_provider = subway_accessibility_provider
        self.bus_client = bus_client
        self.waiting_time_estimator = waiting_time_estimator
        self.current_hour_provider = current_hour_provider

    def get_routes(self, origin: Location, destination: Location) -> list[RouteResult]:
        return [
            self._get_calltaxi_route(origin, destination),
            self._get_subway_route(origin, destination),
            self._get_bus_route(origin, destination),
        ]

    def _get_calltaxi_route(self, origin: Location, destination: Location) -> RouteResult:
        if self.tmap_client is None:
            return _unavailable(TransportType.CALLTAXI, "TMAP app key is not configured")

        try:
            estimate = self.waiting_time_estimator(self.current_hour_provider())
            waiting_seconds = _waiting_seconds(estimate)
        except NotImplementedError:
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 대기시간 예측 모델이 연결되지 않았습니다.")
        except (TypeError, ValueError):
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 대기시간 예측 결과가 유효하지 않습니다.")

        try:
            distance_meters, vehicle_time_seconds = self.tmap_client.get_vehicle_route(origin, destination)
        except TmapRouteError:
            return _unavailable(TransportType.CALLTAXI, "장애인 콜택시 차량 경로를 계산할 수 없습니다.")

        return RouteResult(
            transport_type=TransportType.CALLTAXI,
            status=RouteStatus.AVAILABLE,
            total_time_seconds=waiting_seconds + vehicle_time_seconds,
            total_distance_meters=distance_meters,
            total_cost_won=calculate_seoul_calltaxi_fare(distance_meters),
            walking_distance_meters=None,
            walking_time_seconds=None,
            metric_availability=RouteMetricAvailability(
                walking_distance_meters=MetricAvailability.NOT_AVAILABLE,
                walking_time_seconds=MetricAvailability.NOT_AVAILABLE,
            ),
            accessibility_status=AccessibilityStatus.NOT_VERIFIED,
            summary="장애인 콜택시 경로",
            warnings=[
                f"예측 대기시간 {waiting_seconds}초가 총 이동시간에 포함되었습니다.",
                CALLTAXI_WALKING_WARNING,
                CALLTAXI_ACCESSIBILITY_WARNING,
            ],
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
            warnings=[BUS_ACCESSIBILITY_WARNING, BUS_WALKING_WARNING],
        )


def _waiting_seconds(estimate: WaitingTimeEstimateResult) -> int:
    expected_minutes = getattr(estimate, "expected_minutes", None)
    if isinstance(expected_minutes, bool) or not isinstance(expected_minutes, (int, float)):
        raise TypeError("waiting time estimate expected_minutes must be numeric")
    if not math.isfinite(expected_minutes) or expected_minutes < 0:
        raise ValueError("waiting time estimate must be finite and non-negative")
    return round(expected_minutes * 60)


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
