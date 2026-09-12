"""장애인 콜택시 차량 경로 및 예상요금 API."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts import RouteRequest, RouteResult, RouteStatus, TransportType
from app.core.config import get_settings
from app.services.calltaxi import TmapRouteClient, TmapRouteError, calculate_seoul_calltaxi_fare

router = APIRouter(prefix="/routes", tags=["routes"])


def get_tmap_route_client() -> TmapRouteClient:
    settings = get_settings()
    if not settings.tmap_app_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMAP app key is not configured",
        )
    return TmapRouteClient(app_key=settings.tmap_app_key)


@router.post("/calltaxi", response_model=RouteResult)
def calculate_calltaxi_route(
    request: RouteRequest,
    tmap_route_client: TmapRouteClient = Depends(get_tmap_route_client),
) -> RouteResult:
    """TMAP 자동차 경로안내로 장애인 콜택시 차량 거리·시간·예상요금을 계산한다."""

    try:
        total_distance_meters, total_time_seconds = tmap_route_client.get_vehicle_route(
            origin=request.origin,
            destination=request.destination,
        )
    except TmapRouteError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to calculate calltaxi vehicle route",
        ) from exc

    return RouteResult(
        transport_type=TransportType.CALLTAXI,
        status=RouteStatus.AVAILABLE,
        total_time_seconds=total_time_seconds,
        total_distance_meters=total_distance_meters,
        total_cost_won=calculate_seoul_calltaxi_fare(total_distance_meters),
        walking_distance_meters=0,
        walking_time_seconds=0,
        summary="장애인 콜택시 차량 경로",
    )
