"""지하철 경로 및 접근성 API."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts import RouteRequest, RouteResult, RouteStatus, TransportType
from app.core.config import get_settings
from app.services.subway import (
    EmptySubwayAccessibilityProvider,
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
    # TODO: 지하철 접근성 lookup이 analysis/에 export되면
    # 해당 station accessibility master를 읽는 provider로 교체한다.
    return EmptySubwayAccessibilityProvider()


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

    return RouteResult(
        transport_type=TransportType.SUBWAY,
        status=RouteStatus.AVAILABLE,
        total_time_seconds=route.total_time_seconds,
        total_distance_meters=route.total_distance_meters,
        total_cost_won=route.fare_won,
        walking_distance_meters=route.walking_distance_meters,
        walking_time_seconds=route.walking_time_seconds,
        summary=route.summary,
        warnings=build_accessibility_warnings(route.station_keys, accessibility_provider),
    )
