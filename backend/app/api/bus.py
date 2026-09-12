"""ODsay 버스 경로와 노선 단위 저상버스 접근성 API."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts import RouteRequest, RouteResult, RouteStatus, TransportType
from app.core.config import get_settings
from app.services.bus import (
    CsvLowFloorBusRouteProvider,
    LowFloorBusRouteUnavailableError,
    OdsayBusRouteError,
    OdsayLowFloorBusRouteClient,
)

router = APIRouter(prefix="/routes", tags=["routes"])
logger = logging.getLogger("app.bus")


def get_odsay_low_floor_bus_route_client() -> OdsayLowFloorBusRouteClient:
    settings = get_settings()
    if not settings.odsay_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ODsay API key is not configured",
        )
    try:
        route_provider = CsvLowFloorBusRouteProvider()
    except OdsayBusRouteError as exc:
        logger.warning("low_floor_bus_route_master_unavailable reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Low-floor bus route lookup is not available",
        ) from exc
    return OdsayLowFloorBusRouteClient(api_key=settings.odsay_api_key, route_provider=route_provider)


@router.post("/bus", response_model=RouteResult)
def calculate_low_floor_bus_route(
    request: RouteRequest,
    route_client: OdsayLowFloorBusRouteClient = Depends(get_odsay_low_floor_bus_route_client),
) -> RouteResult:
    """ODsay 버스 전용 경로 중 노선 단위 저상버스 접근성이 확인된 경로를 반환한다."""

    try:
        route = route_client.get_low_floor_bus_route(origin=request.origin, destination=request.destination)
    except LowFloorBusRouteUnavailableError:
        return RouteResult(
            transport_type=TransportType.LOW_FLOOR_BUS,
            status=RouteStatus.UNAVAILABLE,
            unavailable_reason="운행 가능한 저상버스 경로를 확인할 수 없습니다.",
            warnings=["노선 단위 저상버스 정보 기준이며 특정 차량의 실시간 저상버스 여부는 포함하지 않습니다."],
        )
    except OdsayBusRouteError as exc:
        logger.warning("odsay_bus_route_failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to calculate low-floor bus route",
        ) from exc

    return RouteResult(
        transport_type=TransportType.LOW_FLOOR_BUS,
        status=RouteStatus.AVAILABLE,
        total_time_seconds=route.total_time_seconds,
        total_distance_meters=route.total_distance_meters,
        total_cost_won=route.fare_won,
        walking_distance_meters=route.walking_distance_meters,
        walking_time_seconds=route.walking_time_seconds,
        summary=route.summary,
        warnings=[
            "저상버스 접근성은 노선 단위 보유 정보이며 특정 시간·정류장의 저상버스 도착을 보장하지 않습니다.",
            "walking_time_seconds와 walking_distance_meters는 ODsay가 제공한 모든 도보 subPath의 합계이며 실제 보행로 실측값은 아닙니다.",
        ],
    )
