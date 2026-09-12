from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.api.contracts import (
    AccessibilityStatus,
    Location,
    MetricAvailability,
    RouteComparisonResponse,
    RouteMetricAvailability,
    RouteResult,
    RouteStatus,
    TransportType,
)
from app.main import create_app

client = TestClient(create_app(include_sample_routes=True))


def test_route_result_contract_handles_walking_distance_and_time() -> None:
    route = RouteResult(
        transport_type=TransportType.SUBWAY,
        status=RouteStatus.AVAILABLE,
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
            status=RouteStatus.AVAILABLE,
            total_time_seconds=1000,
            total_distance_meters=3000,
            total_cost_won=0,
            walking_distance_meters=-1,
            walking_time_seconds=0,
        )


def test_unavailable_route_uses_reason_without_fake_numbers() -> None:
    route = RouteResult(
        transport_type=TransportType.LOW_FLOOR_BUS,
        status=RouteStatus.UNAVAILABLE,
        unavailable_reason="운행 가능한 저상버스 경로 없음",
    )

    assert route.total_time_seconds is None
    assert route.total_distance_meters is None
    assert route.total_cost_won is None
    assert route.walking_distance_meters is None
    assert route.walking_time_seconds is None
    assert route.unavailable_reason == "운행 가능한 저상버스 경로 없음"


def test_unavailable_route_rejects_fake_zero_metrics() -> None:
    with pytest.raises(ValidationError):
        RouteResult(
            transport_type=TransportType.SUBWAY,
            status=RouteStatus.UNAVAILABLE,
            total_time_seconds=0,
            total_distance_meters=0,
            total_cost_won=0,
            walking_distance_meters=0,
            walking_time_seconds=0,
            unavailable_reason="지하철 경로 없음",
        )


def test_unavailable_route_requires_reason() -> None:
    with pytest.raises(ValidationError):
        RouteResult(
            transport_type=TransportType.CALLTAXI,
            status=RouteStatus.UNAVAILABLE,
        )


def test_available_route_requires_values_for_available_metrics() -> None:
    with pytest.raises(ValidationError):
        RouteResult(
            transport_type=TransportType.CALLTAXI,
            status=RouteStatus.AVAILABLE,
            total_time_seconds=1000,
            total_distance_meters=3000,
            total_cost_won=0,
            walking_distance_meters=100,
        )


def test_calltaxi_available_route_can_express_unknown_walking_metrics() -> None:
    route = RouteResult(
        transport_type=TransportType.CALLTAXI,
        status=RouteStatus.AVAILABLE,
        total_time_seconds=4200,
        total_distance_meters=12_500,
        total_cost_won=2300,
        walking_distance_meters=None,
        walking_time_seconds=None,
        metric_availability=RouteMetricAvailability(
            walking_distance_meters=MetricAvailability.NOT_AVAILABLE,
            walking_time_seconds=MetricAvailability.NOT_AVAILABLE,
        ),
        accessibility_status=AccessibilityStatus.NOT_VERIFIED,
    )

    assert route.walking_distance_meters is None
    assert route.walking_time_seconds is None
    assert route.metric_availability is not None
    assert route.metric_availability.walking_distance_meters == MetricAvailability.NOT_AVAILABLE
    assert route.accessibility_status == AccessibilityStatus.NOT_VERIFIED


def test_not_available_metric_rejects_numeric_value() -> None:
    with pytest.raises(ValidationError):
        RouteResult(
            transport_type=TransportType.CALLTAXI,
            status=RouteStatus.AVAILABLE,
            total_time_seconds=4200,
            total_distance_meters=12_500,
            total_cost_won=2300,
            walking_distance_meters=0,
            walking_time_seconds=None,
            metric_availability=RouteMetricAvailability(
                walking_distance_meters=MetricAvailability.NOT_AVAILABLE,
                walking_time_seconds=MetricAvailability.NOT_AVAILABLE,
            ),
        )


def test_route_result_rejects_walking_time_greater_than_total_time() -> None:
    with pytest.raises(ValidationError):
        RouteResult(
            transport_type=TransportType.SUBWAY,
            status=RouteStatus.AVAILABLE,
            total_time_seconds=300,
            total_distance_meters=2000,
            total_cost_won=0,
            walking_distance_meters=100,
            walking_time_seconds=1000,
        )


def test_route_result_rejects_walking_distance_greater_than_total_distance() -> None:
    with pytest.raises(ValidationError):
        RouteResult(
            transport_type=TransportType.SUBWAY,
            status=RouteStatus.AVAILABLE,
            total_time_seconds=1200,
            total_distance_meters=500,
            total_cost_won=0,
            walking_distance_meters=2000,
            walking_time_seconds=100,
        )


def test_route_result_allows_walking_values_equal_to_total_values() -> None:
    route = RouteResult(
        transport_type=TransportType.SUBWAY,
        status=RouteStatus.AVAILABLE,
        total_time_seconds=300,
        total_distance_meters=500,
        total_cost_won=0,
        walking_distance_meters=500,
        walking_time_seconds=300,
    )

    assert route.walking_distance_meters == route.total_distance_meters
    assert route.walking_time_seconds == route.total_time_seconds


def test_location_accepts_coordinate_boundaries() -> None:
    south_west = Location(latitude=-90, longitude=-180)
    north_east = Location(latitude=90, longitude=180)

    assert south_west.latitude == -90
    assert south_west.longitude == -180
    assert north_east.latitude == 90
    assert north_east.longitude == 180


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (91, 0),
        (0, 181),
        (float("nan"), 0),
        (0, float("inf")),
    ],
)
def test_location_rejects_invalid_coordinates(latitude: float, longitude: float) -> None:
    with pytest.raises(ValidationError):
        Location(latitude=latitude, longitude=longitude)


def _available_route(transport_type: TransportType) -> RouteResult:
    return RouteResult(
        transport_type=transport_type,
        status=RouteStatus.AVAILABLE,
        total_time_seconds=1000,
        total_distance_meters=3000,
        total_cost_won=0,
        walking_distance_meters=100,
        walking_time_seconds=100,
    )


def _comparison_response(routes: list[RouteResult]) -> RouteComparisonResponse:
    return RouteComparisonResponse(
        origin=Location(latitude=37.5666103, longitude=126.9783882),
        destination=Location(latitude=37.5546788, longitude=126.9706069),
        routes=routes,
    )


def test_route_comparison_requires_exactly_three_transport_types() -> None:
    response = _comparison_response(
        [
            _available_route(TransportType.CALLTAXI),
            _available_route(TransportType.SUBWAY),
            _available_route(TransportType.LOW_FLOOR_BUS),
        ]
    )

    assert len(response.routes) == 3


def test_route_comparison_rejects_two_routes() -> None:
    with pytest.raises(ValidationError):
        _comparison_response(
            [
                _available_route(TransportType.CALLTAXI),
                _available_route(TransportType.SUBWAY),
            ]
        )


def test_route_comparison_rejects_four_routes() -> None:
    with pytest.raises(ValidationError):
        _comparison_response(
            [
                _available_route(TransportType.CALLTAXI),
                _available_route(TransportType.SUBWAY),
                _available_route(TransportType.LOW_FLOOR_BUS),
                _available_route(TransportType.CALLTAXI),
            ]
        )


def test_route_comparison_rejects_duplicate_transport_type() -> None:
    with pytest.raises(ValidationError):
        _comparison_response(
            [
                _available_route(TransportType.CALLTAXI),
                _available_route(TransportType.SUBWAY),
                _available_route(TransportType.SUBWAY),
            ]
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
            "status",
            "total_time_seconds",
            "total_distance_meters",
            "total_cost_won",
            "walking_distance_meters",
            "walking_time_seconds",
            "metric_availability",
            "accessibility_status",
            "unavailable_reason",
            "summary",
            "warnings",
        }
        assert route.status == RouteStatus.AVAILABLE
        assert route.walking_distance_meters is not None
        assert route.walking_time_seconds is not None
        assert route.walking_distance_meters <= route.total_distance_meters
        assert route.walking_time_seconds <= route.total_time_seconds


def test_sample_routes_are_not_registered_when_disabled() -> None:
    production_like_app = create_app(include_sample_routes=False)
    production_like_client = TestClient(production_like_app)

    response = production_like_client.get("/routes/sample")

    assert response.status_code == 404


def test_sample_routes_are_not_registered_by_default() -> None:
    default_app = create_app()
    default_client = TestClient(default_app)

    response = default_client.get("/routes/sample")

    assert response.status_code == 404


def test_sample_routes_are_registered_only_when_enabled() -> None:
    sample_app = create_app(include_sample_routes=True)
    sample_client = TestClient(sample_app)

    response = sample_client.get("/routes/sample")

    assert response.status_code == 200
