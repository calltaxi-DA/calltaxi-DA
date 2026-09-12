"""장애인 콜택시 차량 경로 및 예상요금 API."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts import CalltaxiRouteResponse, RouteRequest
from app.core.config import get_settings
from app.services.calltaxi import TmapRouteClient, TmapRouteError, calculate_seoul_calltaxi_fare

router = APIRouter(prefix="/routes", tags=["routes"])
logger = logging.getLogger("app.calltaxi")

CALLTAXI_EXTRA_COST_WARNING = "통행료·주차료 등 추가 비용은 예상요금에 포함되지 않습니다."


def get_tmap_route_client() -> TmapRouteClient:
    settings = get_settings()
    if not settings.tmap_app_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMAP app key is not configured",
        )
    return TmapRouteClient(app_key=settings.tmap_app_key)


@router.post("/calltaxi", response_model=CalltaxiRouteResponse)
def calculate_calltaxi_route(
    request: RouteRequest,
    tmap_route_client: TmapRouteClient = Depends(get_tmap_route_client),
) -> CalltaxiRouteResponse:
    """TMAP 자동차 경로안내로 장애인 콜택시 차량 거리·시간·예상요금을 계산한다."""

    try:
        vehicle_distance_meters, vehicle_time_seconds = tmap_route_client.get_vehicle_route(
            origin=request.origin,
            destination=request.destination,
        )
    except TmapRouteError as exc:
        logger.warning("tmap_route_failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to calculate calltaxi vehicle route",
        ) from exc

    return CalltaxiRouteResponse(
        vehicle_distance_meters=vehicle_distance_meters,
        vehicle_time_seconds=vehicle_time_seconds,
        estimated_fare_won=calculate_seoul_calltaxi_fare(vehicle_distance_meters),
        warnings=[CALLTAXI_EXTRA_COST_WARNING],
    )
