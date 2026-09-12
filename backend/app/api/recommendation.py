"""세 이동수단 결과 통합 및 Rule-based 추천 API."""

from fastapi import APIRouter

from app.api.contracts import RecommendationRequest, RecommendationResponse
from app.services.recommendation import rank_routes

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/recommendations", response_model=RecommendationResponse)
def recommend_routes(request: RecommendationRequest) -> RecommendationResponse:
    """세 이동수단 결과를 사용자 우선순위에 따라 최대 3개까지 정렬한다."""

    recommendations, excluded_routes = rank_routes(request.routes, request.priorities)
    return RecommendationResponse(
        origin=request.origin,
        destination=request.destination,
        priorities=request.priorities,
        recommendations=recommendations,
        excluded_routes=excluded_routes,
    )
