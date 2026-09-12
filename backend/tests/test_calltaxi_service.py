import json

import pytest
import httpx

from app.api.contracts import Location
from app.services.calltaxi import (
    TmapRouteClient,
    TmapRouteError,
    calculate_seoul_calltaxi_fare,
    parse_tmap_route_metrics,
)


@pytest.mark.parametrize(
    ("distance_meters", "expected_fare_won"),
    [
        (0, 1_500),
        (5_000, 1_500),
        (5_001, 1_500),
        (9_999, 2_800),
        (10_000, 2_900),
        (10_001, 2_900),
        (20_000, 3_600),
    ],
)
def test_calculate_seoul_calltaxi_fare(distance_meters: int, expected_fare_won: int) -> None:
    assert calculate_seoul_calltaxi_fare(distance_meters) == expected_fare_won


def test_calculate_seoul_calltaxi_fare_floors_under_100_won() -> None:
    assert calculate_seoul_calltaxi_fare(12_500) == 3_000


def test_parse_tmap_route_metrics() -> None:
    payload = {
        "features": [
            {
                "properties": {
                    "totalDistance": 12_345,
                    "totalTime": 1_234,
                }
            }
        ]
    }

    distance_meters, time_seconds = parse_tmap_route_metrics(payload)

    assert distance_meters == 12_345
    assert time_seconds == 1_234


def test_parse_tmap_route_metrics_rejects_missing_metrics() -> None:
    with pytest.raises(TmapRouteError):
        parse_tmap_route_metrics({"features": []})


def test_parse_tmap_route_metrics_rejects_negative_metrics() -> None:
    with pytest.raises(TmapRouteError):
        parse_tmap_route_metrics(
            {
                "features": [
                    {
                        "properties": {
                            "totalDistance": -1,
                            "totalTime": 1_234,
                        }
                    }
                ]
            }
        )


def test_tmap_route_client_sends_expected_request_without_logging_app_key() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "properties": {
                            "totalDistance": 12_345,
                            "totalTime": 1_234,
                        }
                    }
                ]
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TmapRouteClient(app_key="test-app-key", http_client=http_client)

    distance_meters, time_seconds = client.get_vehicle_route(
        origin=Location(name="서울시청", latitude=37.5666103, longitude=126.9783882),
        destination=Location(name="서울역", latitude=37.5546788, longitude=126.9706069),
    )

    assert distance_meters == 12_345
    assert time_seconds == 1_234
    assert captured_request is not None
    assert str(captured_request.url) == "https://apis.openapi.sk.com/tmap/routes?version=1"
    assert captured_request.headers["appkey"] == "test-app-key"
    assert captured_request.headers["content-type"] == "application/json"
    request_payload = json.loads(captured_request.read())
    assert request_payload["startX"] == 126.9783882
    assert request_payload["startY"] == 37.5666103
    assert request_payload["endX"] == 126.9706069
    assert request_payload["endY"] == 37.5546788
    assert request_payload["reqCoordType"] == "WGS84GEO"
    assert request_payload["resCoordType"] == "WGS84GEO"
    assert request_payload["totalValue"] == 2


def test_tmap_route_client_converts_invalid_json_to_tmap_route_error() -> None:
    http_client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html>error</html>")))
    client = TmapRouteClient(app_key="test-app-key", http_client=http_client)

    with pytest.raises(TmapRouteError) as exc_info:
        client.get_vehicle_route(
            origin=Location(latitude=37.5666103, longitude=126.9783882),
            destination=Location(latitude=37.5546788, longitude=126.9706069),
        )

    assert exc_info.value.reason == "invalid_json"
