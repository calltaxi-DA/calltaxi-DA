from app.api.contracts import (
    AccessibilityStatus,
    MetricAvailability,
    RecommendationPriority,
    RouteMetricAvailability,
    RouteResult,
    RouteStatus,
    TransportType,
)
from app.services.recommendation import rank_routes


def _route(
    transport_type: TransportType,
    *,
    time: int,
    cost: int,
    walk_distance: int | None,
    walk_time: int | None,
    accessibility: AccessibilityStatus = AccessibilityStatus.VERIFIED_AVAILABLE,
) -> RouteResult:
    walking_available = walk_distance is not None and walk_time is not None
    return RouteResult(
        transport_type=transport_type,
        status=RouteStatus.AVAILABLE,
        total_time_seconds=time,
        total_distance_meters=10_000,
        total_cost_won=cost,
        walking_distance_meters=walk_distance,
        walking_time_seconds=walk_time,
        metric_availability=RouteMetricAvailability(
            walking_distance_meters=(
                MetricAvailability.AVAILABLE if walking_available else MetricAvailability.NOT_AVAILABLE
            ),
            walking_time_seconds=(
                MetricAvailability.AVAILABLE if walking_available else MetricAvailability.NOT_AVAILABLE
            ),
        ),
        accessibility_status=accessibility,
    )


def _three_routes() -> list[RouteResult]:
    return [
        _route(TransportType.CALLTAXI, time=1800, cost=2500, walk_distance=None, walk_time=None),
        _route(TransportType.SUBWAY, time=2400, cost=1500, walk_distance=500, walk_time=480),
        _route(TransportType.LOW_FLOOR_BUS, time=3000, cost=1400, walk_distance=300, walk_time=360),
    ]


def test_time_priority_returns_all_three_in_time_order() -> None:
    recommendations, excluded = rank_routes(
        _three_routes(),
        [RecommendationPriority.TIME, RecommendationPriority.COST, RecommendationPriority.WALK],
    )

    assert [item.rank for item in recommendations] == [1, 2, 3]
    assert [item.route.transport_type for item in recommendations] == [
        TransportType.CALLTAXI,
        TransportType.SUBWAY,
        TransportType.LOW_FLOOR_BUS,
    ]
    assert excluded == []


def test_cost_priority_returns_all_three_in_cost_order() -> None:
    recommendations, excluded = rank_routes(
        _three_routes(),
        [RecommendationPriority.COST, RecommendationPriority.TIME, RecommendationPriority.WALK],
    )

    assert [item.route.transport_type for item in recommendations] == [
        TransportType.LOW_FLOOR_BUS,
        TransportType.SUBWAY,
        TransportType.CALLTAXI,
    ]
    assert excluded == []


def test_walk_priority_excludes_calltaxi_with_unknown_walking_metrics() -> None:
    recommendations, excluded = rank_routes(
        _three_routes(),
        [RecommendationPriority.WALK, RecommendationPriority.TIME, RecommendationPriority.COST],
    )

    assert [item.route.transport_type for item in recommendations] == [
        TransportType.LOW_FLOOR_BUS,
        TransportType.SUBWAY,
    ]
    assert len(excluded) == 1
    assert excluded[0].transport_type == TransportType.CALLTAXI
    assert "walk" in excluded[0].reason


def test_secondary_missing_metric_is_ranked_after_exact_primary_tie() -> None:
    routes = _three_routes()
    routes[1].total_time_seconds = 1800

    recommendations, _ = rank_routes(
        routes,
        [RecommendationPriority.TIME, RecommendationPriority.WALK, RecommendationPriority.COST],
    )

    assert [item.route.transport_type for item in recommendations[:2]] == [
        TransportType.SUBWAY,
        TransportType.CALLTAXI,
    ]


def test_verified_unavailable_accessibility_is_excluded() -> None:
    routes = _three_routes()
    routes[1].accessibility_status = AccessibilityStatus.VERIFIED_UNAVAILABLE

    recommendations, excluded = rank_routes(
        routes,
        [RecommendationPriority.TIME, RecommendationPriority.COST, RecommendationPriority.WALK],
    )

    assert TransportType.SUBWAY not in [item.route.transport_type for item in recommendations]
    assert excluded[0].transport_type == TransportType.SUBWAY


def test_stable_transport_order_breaks_complete_tie() -> None:
    routes = [
        _route(TransportType.LOW_FLOOR_BUS, time=1000, cost=1000, walk_distance=100, walk_time=100),
        _route(TransportType.SUBWAY, time=1000, cost=1000, walk_distance=100, walk_time=100),
        _route(TransportType.CALLTAXI, time=1000, cost=1000, walk_distance=100, walk_time=100),
    ]

    recommendations, _ = rank_routes(routes, list(RecommendationPriority))

    assert [item.route.transport_type for item in recommendations] == [
        TransportType.CALLTAXI,
        TransportType.SUBWAY,
        TransportType.LOW_FLOOR_BUS,
    ]
