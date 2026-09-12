from fastapi.testclient import TestClient

from app.api.contracts import RecommendationResponse
from app.main import create_app

client = TestClient(create_app())


def _payload(priorities: list[str]) -> dict[str, object]:
    origin = {"name": "서울시청", "latitude": 37.5666, "longitude": 126.9784}
    destination = {"name": "강남역", "latitude": 37.4979, "longitude": 127.0276}
    routes = [
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
    return {"origin": origin, "destination": destination, "routes": routes, "priorities": priorities}


def test_recommendations_returns_top_three_for_time_priority() -> None:
    response = client.post("/routes/recommendations", json=_payload(["time", "cost", "walk"]))

    assert response.status_code == 200
    parsed = RecommendationResponse.model_validate(response.json())
    assert [item.rank for item in parsed.recommendations] == [1, 2, 3]
    assert [item.route.transport_type.value for item in parsed.recommendations] == [
        "calltaxi",
        "subway",
        "low_floor_bus",
    ]
    assert parsed.excluded_routes == []


def test_recommendations_returns_top_three_for_cost_priority() -> None:
    response = client.post("/routes/recommendations", json=_payload(["cost", "time", "walk"]))

    assert response.status_code == 200
    assert [item["route"]["transport_type"] for item in response.json()["recommendations"]] == [
        "low_floor_bus",
        "subway",
        "calltaxi",
    ]


def test_recommendations_excludes_unknown_primary_walking_metric() -> None:
    response = client.post("/routes/recommendations", json=_payload(["walk", "time", "cost"]))

    assert response.status_code == 200
    payload = response.json()
    assert [item["route"]["transport_type"] for item in payload["recommendations"]] == [
        "low_floor_bus",
        "subway",
    ]
    assert payload["excluded_routes"][0]["transport_type"] == "calltaxi"
    assert "walk" in payload["excluded_routes"][0]["reason"]


def test_recommendations_returns_top_three_for_walk_priority_when_all_metrics_are_available() -> None:
    payload = _payload(["walk", "time", "cost"])
    calltaxi = payload["routes"][0]  # type: ignore[index]
    calltaxi["walking_distance_meters"] = 100
    calltaxi["walking_time_seconds"] = 120
    calltaxi["metric_availability"] = {
        "walking_distance_meters": "available",
        "walking_time_seconds": "available",
    }

    response = client.post("/routes/recommendations", json=payload)

    assert response.status_code == 200
    assert [item["route"]["transport_type"] for item in response.json()["recommendations"]] == [
        "calltaxi",
        "low_floor_bus",
        "subway",
    ]
    assert response.json()["excluded_routes"] == []


def test_recommendations_rejects_duplicate_priorities() -> None:
    response = client.post("/routes/recommendations", json=_payload(["time", "time", "walk"]))

    assert response.status_code == 422


def test_recommendations_rejects_missing_transport_type() -> None:
    payload = _payload(["time", "cost", "walk"])
    payload["routes"] = payload["routes"][:2]  # type: ignore[index]

    response = client.post("/routes/recommendations", json=payload)

    assert response.status_code == 422
