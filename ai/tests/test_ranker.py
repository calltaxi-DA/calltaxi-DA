from ai.recommendation.ranker import RouteCandidate, rank_routes


def _candidates() -> list[RouteCandidate]:
    return [
        RouteCandidate(mode="subway", cost=0, total_minutes=34, walk_meters=320),
        RouteCandidate(mode="low_floor_bus", cost=1500, total_minutes=41, walk_meters=170),
        RouteCandidate(mode="call_taxi", cost=3000, total_minutes=52, walk_meters=20),
    ]


def test_rank_by_cost_prefers_free_route_first() -> None:
    ranked = rank_routes(_candidates(), priority="cost")

    assert ranked[0].mode == "subway"


def test_rank_by_time_prefers_shortest_total_minutes() -> None:
    ranked = rank_routes(_candidates(), priority="time")

    assert ranked[0].mode == "subway"


def test_rank_by_walk_prefers_shortest_walk() -> None:
    ranked = rank_routes(_candidates(), priority="walk")

    assert ranked[0].mode == "call_taxi"
