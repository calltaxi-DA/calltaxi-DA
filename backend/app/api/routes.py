"""경로 비교 API 계약 확인용 라우터.

실제 경로 계산, 외부 지도 API 호출, 추천 정렬은 이후 Phase에서 구현한다.
"""

from fastapi import APIRouter

from app.api.contracts import Location, RouteComparisonResponse, RouteResult, TransportType

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("/sample", response_model=RouteComparisonResponse)
def get_sample_routes() -> RouteComparisonResponse:
    """3개 이동수단이 동일한 RouteResult 형식으로 반환되는지 확인한다."""

    origin = Location(
        name="서울시청",
        latitude=37.5666103,
        longitude=126.9783882,
        address="서울 중구",
    )
    destination = Location(
        name="서울역",
        latitude=37.5546788,
        longitude=126.9706069,
        address="서울 용산구",
    )

    return RouteComparisonResponse(
        origin=origin,
        destination=destination,
        routes=[
            RouteResult(
                transport_type=TransportType.CALLTAXI,
                total_time_seconds=1800,
                total_distance_meters=3200,
                total_cost_won=0,
                walking_distance_meters=0,
                walking_time_seconds=0,
                summary="장애인 콜택시 샘플 경로",
            ),
            RouteResult(
                transport_type=TransportType.SUBWAY,
                total_time_seconds=1500,
                total_distance_meters=2800,
                total_cost_won=0,
                walking_distance_meters=450,
                walking_time_seconds=420,
                summary="지하철 샘플 경로",
            ),
            RouteResult(
                transport_type=TransportType.LOW_FLOOR_BUS,
                total_time_seconds=1700,
                total_distance_meters=3000,
                total_cost_won=0,
                walking_distance_meters=300,
                walking_time_seconds=300,
                summary="저상버스 샘플 경로",
            ),
        ],
    )
