"""지하철 경로 및 접근성 API."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts import RouteRequest, RouteResult, RouteStatus, TransportType
from app.core.config import get_settings
from app.services.subway import (
    CsvSubwayAccessibilityProvider,
    OdsayRouteError,
    OdsaySubwayRouteClient,
    SubwayAccessibilityProvider,
    build_accessibility_warnings,
)

router = APIRouter(prefix="/routes", tags=["routes"])
logger = logging.getLogger("app.subway")


def get_odsay_subway_route_client() -> OdsaySubwayRouteClient:
    settings = get_settings()
    if not settings.odsay_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ODsay API key is not configured",
        )
    return OdsaySubwayRouteClient(api_key=settings.odsay_api_key)


def get_subway_accessibility_provider() -> SubwayAccessibilityProvider:
    try:
        return CsvSubwayAccessibilityProvider()
    except OdsayRouteError as exc:
        logger.warning("subway_accessibility_lookup_unavailable reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Subway accessibility lookup is not available",
        ) from exc


@router.post("/subway", response_model=RouteResult)
def calculate_subway_route(
    request: RouteRequest,
    odsay_route_client: OdsaySubwayRouteClient = Depends(get_odsay_subway_route_client),
    accessibility_provider: SubwayAccessibilityProvider = Depends(get_subway_accessibility_provider),
) -> RouteResult:
    """ODsay 지하철 경로에 도보거리·도보시간과 접근성 주의사항을 결합한다."""

    try:
        route = odsay_route_client.get_subway_route(origin=request.origin, destination=request.destination)
    except OdsayRouteError as exc:
        logger.warning("odsay_subway_route_failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to calculate subway route",
        ) from exc

    warnings = build_accessibility_warnings(route.station_keys, accessibility_provider)
    warnings.append(
        "walking_time_seconds와 walking_distance_meters는 ODsay가 제공한 도보 subPath 기준입니다. 지하철 환승 내부 도보시간·거리는 별도 검증 전까지 총 도보값으로 단정하지 않습니다."
    )

    return RouteResult(
        transport_type=TransportType.SUBWAY,
        status=RouteStatus.AVAILABLE,
        total_time_seconds=route.total_time_seconds,
        total_distance_meters=route.total_distance_meters,
        total_cost_won=route.fare_won,
        walking_distance_meters=route.walking_distance_meters,
        walking_time_seconds=route.walking_time_seconds,
        summary=route.summary,
        warnings=warnings,
    )
