"""이동수단 경로를 사용자 우선순위로 정렬하는 Rule-based 서비스."""

from functools import cmp_to_key
from typing import Protocol

from app.api.contracts import (
    AccessibilityStatus,
    ExcludedRoute,
    Location,
    MetricAvailability,
    RankedRoute,
    RecommendationPriority,
    RouteResult,
    RouteStatus,
    TransportType,
)


class RecommendationRouteProvider(Protocol):
    """Backend 소유 데이터로 세 이동수단 경로를 생성하는 provider."""

    def get_routes(self, origin: Location, destination: Location) -> list[RouteResult]:
        ...


def rank_routes(
    routes: list[RouteResult], priorities: list[RecommendationPriority]
) -> tuple[list[RankedRoute], list[ExcludedRoute]]:
    """1순위 지표를 사용할 수 있는 경로를 최대 3개까지 사전식 정렬한다."""

    _validate_inputs(routes, priorities)
    primary_priority = priorities[0]
    candidates: list[RouteResult] = []
    excluded: list[ExcludedRoute] = []

    for route in routes:
        reason = _exclusion_reason(route, primary_priority)
        if reason is None:
            candidates.append(route)
        else:
            excluded.append(ExcludedRoute(transport_type=route.transport_type, reason=reason))

    ordered = sorted(candidates, key=cmp_to_key(lambda left, right: _compare(left, right, priorities)))
    recommendations = [RankedRoute(rank=index, route=route) for index, route in enumerate(ordered[:3], start=1)]
    return recommendations, excluded


def _validate_inputs(routes: list[RouteResult], priorities: list[RecommendationPriority]) -> None:
    if len(routes) != len(TransportType) or {route.transport_type for route in routes} != set(TransportType):
        raise ValueError("routes must contain each TransportType exactly once")
    if len(priorities) != len(RecommendationPriority) or set(priorities) != set(RecommendationPriority):
        raise ValueError("priorities must contain each RecommendationPriority exactly once")


def _exclusion_reason(route: RouteResult, primary_priority: RecommendationPriority) -> str | None:
    if route.status == RouteStatus.UNAVAILABLE:
        return route.unavailable_reason or "경로를 이용할 수 없습니다."
    if route.accessibility_status == AccessibilityStatus.VERIFIED_UNAVAILABLE:
        return "검토된 접근성 핵심 조건을 충족하지 못했습니다."
    if not _priority_is_available(route, primary_priority):
        return f"1순위 {primary_priority.value} 지표를 사용할 수 없습니다."
    return None


def _compare(
    left: RouteResult,
    right: RouteResult,
    priorities: list[RecommendationPriority],
) -> int:
    for priority in priorities:
        left_value = _priority_value(left, priority)
        right_value = _priority_value(right, priority)
        if left_value is None and right_value is None:
            continue
        if left_value is None:
            return 1
        if right_value is None:
            return -1
        if left_value < right_value:
            return -1
        if left_value > right_value:
            return 1

    return _transport_tiebreaker(left) - _transport_tiebreaker(right)


def _priority_is_available(route: RouteResult, priority: RecommendationPriority) -> bool:
    return _priority_value(route, priority) is not None


def _priority_value(route: RouteResult, priority: RecommendationPriority) -> tuple[int, ...] | None:
    availability = route.metric_availability
    if availability is None:
        return None

    if priority == RecommendationPriority.TIME:
        if availability.total_time_seconds != MetricAvailability.AVAILABLE or route.total_time_seconds is None:
            return None
        return (route.total_time_seconds,)
    if priority == RecommendationPriority.COST:
        if availability.total_cost_won != MetricAvailability.AVAILABLE or route.total_cost_won is None:
            return None
        return (route.total_cost_won,)
    if (
        availability.walking_distance_meters != MetricAvailability.AVAILABLE
        or availability.walking_time_seconds != MetricAvailability.AVAILABLE
        or route.walking_distance_meters is None
        or route.walking_time_seconds is None
    ):
        return None
    return (route.walking_distance_meters, route.walking_time_seconds)


def _transport_tiebreaker(route: RouteResult) -> int:
    stable_order = {
        "calltaxi": 0,
        "subway": 1,
        "low_floor_bus": 2,
    }
    return stable_order[route.transport_type.value]
