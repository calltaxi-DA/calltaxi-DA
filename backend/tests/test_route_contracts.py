from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.api.contracts import Location, RouteComparisonResponse, RouteResult, TransportType
from app.main import app

client = TestClient(app)


def test_route_result_contract_handles_walking_distance_and_time() -> None:
    route = RouteResult(
        transport_type=TransportType.SUBWAY,
        total_time_seconds=1200,
        total_distance_meters=5000,
        total_cost_won=0,
        walking_distance_meters=350,
        walking_time_seconds=300,
    )

    assert route.walking_distance_meters == 350
    assert route.walking_time_seconds == 300


def test_route_result_contract_rejects_negative_units() -> None:
    with pytest.raises(ValidationError):
        RouteResult(
            transport_type=TransportType.CALLTAXI,
            total_time_seconds=1000,
            total_distance_meters=3000,
            total_cost_won=0,
            walking_distance_meters=-1,
            walking_time_seconds=0,
        )


def test_sample_routes_return_three_transport_types_with_same_shape() -> None:
    response = client.get("/routes/sample")

    assert response.status_code == 200
    payload = response.json()
    parsed = RouteComparisonResponse.model_validate(payload)

    assert isinstance(parsed.origin, Location)
    assert isinstance(parsed.destination, Location)
    assert {route.transport_type for route in parsed.routes} == {
        TransportType.CALLTAXI,
        TransportType.SUBWAY,
        TransportType.LOW_FLOOR_BUS,
    }

    for route in parsed.routes:
        route_payload = route.model_dump()
        assert set(route_payload) == {
            "transport_type",
            "total_time_seconds",
            "total_distance_meters",
            "total_cost_won",
            "walking_distance_meters",
            "walking_time_seconds",
            "summary",
            "warnings",
        }
        assert route.walking_distance_meters >= 0
        assert route.walking_time_seconds >= 0
