"""세 이동수단 결과 통합 및 Rule-based 추천 API."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends

from ai.waiting_time.estimator import estimate_waiting_minutes_for_input
from app.api.contracts import RecommendationRequest, RecommendationResponse
from app.core.config import get_settings
from app.services.bus import CsvLowFloorBusRouteProvider, OdsayBusRouteError, OdsayLowFloorBusRouteClient
from app.services.calltaxi import TmapRouteClient
from app.services.recommendation import RecommendationRouteProvider, rank_routes
from app.services.route_orchestration import BackendRecommendationRouteProvider
from app.services.subway import CsvSubwayAccessibilityProvider, OdsayRouteError, OdsaySubwayRouteClient
from app.services.waiting_time_features import (
    ConfiguredWaitingTimeInputBuilder,
    JsonVehicleOperationCountProvider,
    JsonWeatherObservationProvider,
)

router = APIRouter(prefix="/routes", tags=["routes"])
logger = logging.getLogger("app.recommendation")
SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


def get_recommendation_route_provider() -> RecommendationRouteProvider:
    """설정된 Backend service와 AI Adapter를 조합한 운영 provider를 만든다."""

    settings = get_settings()
    tmap_client = TmapRouteClient(settings.tmap_app_key) if settings.tmap_app_key else None
    subway_client = OdsaySubwayRouteClient(settings.odsay_api_key) if settings.odsay_api_key else None

    try:
        subway_accessibility_provider = CsvSubwayAccessibilityProvider()
    except OdsayRouteError as exc:
        logger.warning("subway_accessibility_lookup_unavailable reason=%s", exc.reason)
        subway_accessibility_provider = None

    bus_client = None
    if settings.odsay_api_key:
        try:
            bus_route_provider = CsvLowFloorBusRouteProvider()
            bus_client = OdsayLowFloorBusRouteClient(settings.odsay_api_key, bus_route_provider)
        except OdsayBusRouteError as exc:
            logger.warning("low_floor_bus_route_master_unavailable reason=%s", exc.reason)

    waiting_time_input_builder = None
    operation_count_lookup_path = settings.resolved_calltaxi_operation_count_lookup_path
    weather_lookup_path = settings.resolved_seoul_weather_observation_lookup_path
    if operation_count_lookup_path is not None and weather_lookup_path is not None:
        waiting_time_input_builder = ConfiguredWaitingTimeInputBuilder(
            operation_count_provider=JsonVehicleOperationCountProvider(operation_count_lookup_path),
            weather_provider=JsonWeatherObservationProvider(weather_lookup_path),
        )

    return BackendRecommendationRouteProvider(
        tmap_client=tmap_client,
        subway_client=subway_client,
        subway_accessibility_provider=subway_accessibility_provider,
        bus_client=bus_client,
        waiting_time_estimator=estimate_waiting_minutes_for_input,
        waiting_time_input_builder=waiting_time_input_builder,
        current_time_provider=lambda: datetime.now(SEOUL_TIMEZONE),
    )


@router.post("/recommendations", response_model=RecommendationResponse)
def recommend_routes(
    request: RecommendationRequest,
    route_provider: RecommendationRouteProvider = Depends(get_recommendation_route_provider),
) -> RecommendationResponse:
    """세 이동수단 결과를 사용자 우선순위에 따라 최대 3개까지 정렬한다."""

    routes = route_provider.get_routes(
        request.origin,
        request.destination,
        request.transport_types,
        request.calltaxi_purpose,
    )
    recommendations, excluded_routes = rank_routes(routes, request.priorities)
    return RecommendationResponse(
        origin=request.origin,
        destination=request.destination,
        transport_types=request.transport_types,
        priorities=request.priorities,
        recommendations=recommendations,
        excluded_routes=excluded_routes,
    )
