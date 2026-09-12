"""세 이동수단 결과 통합 및 Rule-based 추천 API."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts import RecommendationRequest, RecommendationResponse
from app.services.recommendation import RecommendationRouteProvider, rank_routes

router = APIRouter(prefix="/routes", tags=["routes"])


def get_recommendation_route_provider() -> RecommendationRouteProvider:
    """통합 경로 provider가 준비되지 않은 동안 공개 추천을 fail-closed한다."""

    # TODO: 통합 대기시간 Prediction 모델이 ai/waiting_time/estimator.py에 연결되면
    # TMAP 콜택시, ODsay 지하철, ODsay 저상버스 service를 조합한 provider로 대체한다.
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Integrated route provider is not available",
    )


@router.post("/recommendations", response_model=RecommendationResponse)
def recommend_routes(
    request: RecommendationRequest,
    route_provider: RecommendationRouteProvider = Depends(get_recommendation_route_provider),
) -> RecommendationResponse:
    """세 이동수단 결과를 사용자 우선순위에 따라 최대 3개까지 정렬한다."""

    routes = route_provider.get_routes(request.origin, request.destination)
    recommendations, excluded_routes = rank_routes(routes, request.priorities)
    return RecommendationResponse(
        origin=request.origin,
        destination=request.destination,
        priorities=request.priorities,
        recommendations=recommendations,
        excluded_routes=excluded_routes,
    )
