"""교통비 기록 생성과 날짜·월별 조회 API."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.contracts import (
    DailyTransportCostResponse,
    MonthlyTransportCostResponse,
    RecommendationPriority,
    TransportCostRecord,
    TransportCostRecordCreate,
)
from app.api.recommendation import get_recommendation_route_provider
from app.core.config import get_settings
from app.services.recommendation import RecommendationRouteProvider, rank_routes
from app.services.transport_costs import SqliteTransportCostRepository, TransportCostRepositoryError

router = APIRouter(prefix="/transport-cost-records", tags=["transport-costs"])


def get_transport_cost_repository() -> SqliteTransportCostRepository:
    return SqliteTransportCostRepository(get_settings().resolved_transport_cost_db_path)


@router.post("", response_model=TransportCostRecord, status_code=status.HTTP_201_CREATED)
def create_transport_cost_record(
    request: TransportCostRecordCreate,
    route_provider: RecommendationRouteProvider = Depends(get_recommendation_route_provider),
    repository: SqliteTransportCostRepository = Depends(get_transport_cost_repository),
) -> TransportCostRecord:
    routes = route_provider.get_routes(request.origin, request.destination, request.transport_types)
    recommendations, _ = rank_routes(
        routes,
        [RecommendationPriority.COST, RecommendationPriority.TIME, RecommendationPriority.WALK],
    )
    if not recommendations or recommendations[0].route.total_cost_won is None:
        raise HTTPException(status_code=503, detail="금액 우선 추천 비용을 계산할 수 없습니다.")
    recommended_route = recommendations[0].route
    try:
        return repository.add(
            travel_date=request.travel_date,
            actual_cost_won=request.actual_cost_won,
            recommended_cost_won=recommended_route.total_cost_won,
            selected_transport_type=request.selected_transport_type,
            recommended_transport_type=recommended_route.transport_type,
            origin=request.origin,
            destination=request.destination,
        )
    except TransportCostRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/daily", response_model=DailyTransportCostResponse)
def get_daily_transport_costs(
    date_: date = Query(alias="date"),
    repository: SqliteTransportCostRepository = Depends(get_transport_cost_repository),
) -> DailyTransportCostResponse:
    try:
        return repository.daily(date_)
    except TransportCostRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/monthly", response_model=MonthlyTransportCostResponse)
def get_monthly_transport_costs(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    repository: SqliteTransportCostRepository = Depends(get_transport_cost_repository),
) -> MonthlyTransportCostResponse:
    try:
        return repository.monthly(month)
    except TransportCostRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
