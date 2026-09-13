from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.contracts import Location, RouteResult
from app.api.recommendation import get_recommendation_route_provider
from app.api.transport_costs import get_transport_cost_repository
from app.main import create_app
from app.services.transport_costs import SqliteTransportCostRepository


class FakeRouteProvider:
    def get_routes(self, origin: Location, destination: Location, transport_types) -> list[RouteResult]:
        costs = {"calltaxi": 2500, "subway": 1500, "low_floor_bus": 1400}
        return [
            RouteResult(
                transport_type=transport_type,
                status="available",
                total_time_seconds=1800,
                total_distance_meters=10000,
                total_cost_won=costs[transport_type.value],
                walking_distance_meters=300,
                walking_time_seconds=360,
            )
            for transport_type in transport_types
        ]


class NoCostRouteProvider:
    def get_routes(self, origin: Location, destination: Location, transport_types) -> list[RouteResult]:
        return [
            RouteResult(
                transport_type=transport_type,
                status="available",
                total_time_seconds=1800,
                total_distance_meters=10000,
                total_cost_won=None,
                walking_distance_meters=300,
                walking_time_seconds=360,
                metric_availability={"total_cost_won": "not_available"},
            )
            for transport_type in transport_types
        ]


def _payload(actual_cost_won: int = 2000) -> dict[str, object]:
    return {
        "travel_date": "2026-09-13",
        "actual_cost_won": actual_cost_won,
        "selected_transport_type": "subway",
        "origin": {"name": "서울시청", "latitude": 37.5666, "longitude": 126.9784},
        "destination": {"name": "강남역", "latitude": 37.4979, "longitude": 127.0276},
        "transport_types": ["subway", "low_floor_bus"],
    }


def _client(tmp_path: Path, provider=None) -> TestClient:
    app = create_app()
    repository = SqliteTransportCostRepository(tmp_path / "costs.sqlite3")
    app.dependency_overrides[get_transport_cost_repository] = lambda: repository
    app.dependency_overrides[get_recommendation_route_provider] = lambda: provider or FakeRouteProvider()
    return TestClient(app)


def test_create_and_query_daily_transport_cost_record(tmp_path: Path) -> None:
    client = _client(tmp_path)

    created = client.post("/transport-cost-records", json=_payload())

    assert created.status_code == 201
    assert created.json()["recommended_transport_type"] == "low_floor_bus"
    assert created.json()["recommended_cost_won"] == 1400
    assert created.json()["potential_savings_won"] == 600

    response = client.get("/transport-cost-records/daily", params={"date": "2026-09-13"})
    assert response.status_code == 200
    assert len(response.json()["records"]) == 1
    assert response.json()["totals"] == {
        "actual_cost_won": 2000,
        "recommended_cost_won": 1400,
        "potential_savings_won": 600,
    }


def test_monthly_summary_groups_dates_and_clamps_negative_savings(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.post("/transport-cost-records", json=_payload(1000)).status_code == 201
    second = _payload(2400)
    second["travel_date"] = "2026-09-14"
    assert client.post("/transport-cost-records", json=second).status_code == 201

    response = client.get("/transport-cost-records/monthly", params={"month": "2026-09"})

    assert response.status_code == 200
    assert [item["date"] for item in response.json()["daily_summaries"]] == ["2026-09-13", "2026-09-14"]
    assert response.json()["totals"] == {
        "actual_cost_won": 3400,
        "recommended_cost_won": 2800,
        "potential_savings_won": 1000,
    }


def test_create_rejects_invalid_transport_selection(tmp_path: Path) -> None:
    payload = _payload()
    payload["selected_transport_type"] = "calltaxi"
    assert _client(tmp_path).post("/transport-cost-records", json=payload).status_code == 422


def test_create_fails_closed_when_cost_recommendation_is_unavailable(tmp_path: Path) -> None:
    response = _client(tmp_path, NoCostRouteProvider()).post("/transport-cost-records", json=_payload())
    assert response.status_code == 503
    assert not (tmp_path / "costs.sqlite3").exists()


def test_query_rejects_invalid_date_and_month(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/transport-cost-records/daily", params={"date": "2026-02-30"}).status_code == 422
    assert client.get("/transport-cost-records/monthly", params={"month": "2026-13"}).status_code == 422


def test_empty_daily_query_returns_zero_totals(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/transport-cost-records/daily", params={"date": date.today().isoformat()})
    assert response.status_code == 200
    assert response.json()["records"] == []
    assert response.json()["totals"]["actual_cost_won"] == 0
