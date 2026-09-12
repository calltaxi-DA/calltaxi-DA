from fastapi.testclient import TestClient

from app.api.contracts import Location, RecommendationResponse, RouteResult
from app.api.recommendation import get_recommendation_route_provider
from app.main import create_app

client = TestClient(create_app())


def _routes() -> list[dict[str, object]]:
    return [
        {
            "transport_type": "calltaxi",
            "status": "available",
            "total_time_seconds": 1800,
            "total_distance_meters": 12000,
            "total_cost_won": 2500,
            "walking_distance_meters": None,
            "walking_time_seconds": None,
            "metric_availability": {
                "walking_distance_meters": "not_available",
                "walking_time_seconds": "not_available",
            },
            "accessibility_status": "not_verified",
            "warnings": ["콜택시 접근 도보와 이용 자격이 확인되지 않았습니다."],
        },
        {
            "transport_type": "subway",
            "status": "available",
            "total_time_seconds": 2400,
            "total_distance_meters": 13000,
            "total_cost_won": 1500,
            "walking_distance_meters": 500,
            "walking_time_seconds": 480,
            "accessibility_status": "verified_available",
        },
        {
            "transport_type": "low_floor_bus",
            "status": "available",
            "total_time_seconds": 3000,
            "total_distance_meters": 14000,
            "total_cost_won": 1400,
            "walking_distance_meters": 300,
            "walking_time_seconds": 360,
            "accessibility_status": "verified_available",
        },
    ]


class FakeRecommendationRouteProvider:
    def __init__(self, routes: list[dict[str, object]] | None = None) -> None:
        self.routes = [RouteResult.model_validate(route) for route in (routes or _routes())]
        self.calls: list[tuple[Location, Location]] = []

    def get_routes(self, origin: Location, destination: Location) -> list[RouteResult]:
        self.calls.append((origin, destination))
        return self.routes


def _payload(priorities: list[str]) -> dict[str, object]:
    origin = {"name": "서울시청", "latitude": 37.5666, "longitude": 126.9784}
    destination = {"name": "강남역", "latitude": 37.4979, "longitude": 127.0276}
    return {"origin": origin, "destination": destination, "priorities": priorities}


def _client_with_provider(
    provider: FakeRecommendationRouteProvider | None = None,
) -> tuple[TestClient, FakeRecommendationRouteProvider]:
    app = create_app()
    fake_provider = provider or FakeRecommendationRouteProvider()
    app.dependency_overrides[get_recommendation_route_provider] = lambda: fake_provider
    return TestClient(app), fake_provider


def test_recommendations_returns_top_three_for_time_priority() -> None:
    override_client, provider = _client_with_provider()
    request_payload = _payload(["time", "cost", "walk"])

    response = override_client.post("/routes/recommendations", json=request_payload)

    assert response.status_code == 200
    parsed = RecommendationResponse.model_validate(response.json())
    assert [item.rank for item in parsed.recommendations] == [1, 2, 3]
    assert [item.route.transport_type.value for item in parsed.recommendations] == [
        "calltaxi",
        "subway",
        "low_floor_bus",
    ]
    assert parsed.excluded_routes == []
    assert len(provider.calls) == 1
    assert provider.calls[0][0].latitude == 37.5666


def test_recommendations_returns_top_three_for_cost_priority() -> None:
    override_client, _ = _client_with_provider()
    response = override_client.post("/routes/recommendations", json=_payload(["cost", "time", "walk"]))

    assert response.status_code == 200
    assert [item["route"]["transport_type"] for item in response.json()["recommendations"]] == [
        "low_floor_bus",
        "subway",
        "calltaxi",
    ]


def test_recommendations_excludes_unknown_primary_walking_metric() -> None:
    override_client, _ = _client_with_provider()
    response = override_client.post("/routes/recommendations", json=_payload(["walk", "time", "cost"]))

    assert response.status_code == 200
    payload = response.json()
    assert [item["route"]["transport_type"] for item in payload["recommendations"]] == [
        "low_floor_bus",
        "subway",
    ]
    assert payload["excluded_routes"][0]["transport_type"] == "calltaxi"
    assert "walk" in payload["excluded_routes"][0]["reason"]


def test_recommendations_returns_top_three_for_walk_priority_when_all_metrics_are_available() -> None:
    routes = _routes()
    calltaxi = routes[0]
    calltaxi["walking_distance_meters"] = 100
    calltaxi["walking_time_seconds"] = 120
    calltaxi["metric_availability"] = {
        "walking_distance_meters": "available",
        "walking_time_seconds": "available",
    }

    override_client, _ = _client_with_provider(FakeRecommendationRouteProvider(routes))
    response = override_client.post("/routes/recommendations", json=_payload(["walk", "time", "cost"]))

    assert response.status_code == 200
    assert [item["route"]["transport_type"] for item in response.json()["recommendations"]] == [
        "calltaxi",
        "low_floor_bus",
        "subway",
    ]
    assert response.json()["excluded_routes"] == []


def test_recommendations_rejects_duplicate_priorities() -> None:
    override_client, _ = _client_with_provider()
    response = override_client.post("/routes/recommendations", json=_payload(["time", "time", "walk"]))

    assert response.status_code == 422


def test_recommendations_rejects_client_supplied_routes() -> None:
    override_client, _ = _client_with_provider()
    payload = _payload(["time", "cost", "walk"])
    payload["routes"] = _routes()

    response = override_client.post("/routes/recommendations", json=payload)

    assert response.status_code == 422


def test_recommendations_fail_closed_until_backend_provider_is_connected() -> None:
    response = client.post("/routes/recommendations", json=_payload(["time", "cost", "walk"]))

    assert response.status_code == 503
    assert response.json() == {"detail": "Integrated route provider is not available"}
