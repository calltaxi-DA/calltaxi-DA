import json

import httpx
import pytest

from app.api.contracts import Location
from app.services.subway import (
    CsvSubwayAccessibilityProvider,
    OdsayRouteError,
    OdsaySubwayRouteClient,
    StationAccessibility,
    SubwayStationKey,
    build_accessibility_warnings,
    parse_odsay_subway_route,
)


def _odsay_payload() -> dict:
    return {
        "result": {
            "path": [
                {
                    "pathType": 1,
                    "info": {
                        "totalTime": 37,
                        "totalDistance": 9200,
                        "payment": 1400,
                    },
                    "subPath": [
                        {"trafficType": 3, "distance": 320, "sectionTime": 5},
                        {
                            "trafficType": 1,
                            "distance": 4600,
                            "sectionTime": 14,
                            "startName": "서울역",
                            "endName": "시청",
                            "lane": [{"name": "1호선"}],
                        },
                        {"trafficType": 3, "distance": 110, "sectionTime": 2},
                        {
                            "trafficType": 1,
                            "distance": 3920,
                            "sectionTime": 12,
                            "startName": "시청",
                            "endName": "강남역",
                            "lane": [{"name": "2호선"}],
                        },
                        {"trafficType": 3, "distance": 250, "sectionTime": 4},
                    ],
                }
            ]
        }
    }


def test_parse_odsay_subway_route_sums_total_walking_distance_and_time() -> None:
    route = parse_odsay_subway_route(_odsay_payload())

    assert route.total_time_seconds == 37 * 60
    assert route.total_distance_meters == 9_200
    assert route.walking_distance_meters == 680
    assert route.walking_time_seconds == 11 * 60
    assert route.fare_won == 1_400
    assert route.station_keys == (
        SubwayStationKey(line_name="1호선", station_name="서울"),
        SubwayStationKey(line_name="1호선", station_name="시청"),
        SubwayStationKey(line_name="2호선", station_name="시청"),
        SubwayStationKey(line_name="2호선", station_name="강남"),
    )
    assert route.summary == "서울역 → 강남역 지하철 경로"


def test_parse_odsay_subway_route_rejects_missing_subway_route() -> None:
    payload = {"result": {"path": [{"pathType": 3, "info": {"totalTime": 5}, "subPath": [{"trafficType": 3}]}]}}

    with pytest.raises(OdsayRouteError) as exc_info:
        parse_odsay_subway_route(payload)

    assert exc_info.value.reason == "missing_subway_route"


def test_parse_odsay_subway_route_skips_bus_and_subway_mixed_route() -> None:
    payload = {
        "result": {
            "path": [
                {
                    "pathType": 3,
                    "info": {"totalTime": 20, "totalDistance": 5_000, "payment": 1_500},
                    "subPath": [
                        {"trafficType": 2, "distance": 1_000, "sectionTime": 5},
                        {
                            "trafficType": 1,
                            "distance": 3_000,
                            "sectionTime": 10,
                            "startName": "서울역",
                            "endName": "시청",
                            "lane": [{"name": "1호선"}],
                        },
                    ],
                },
                {
                    "pathType": 1,
                    "info": {"totalTime": 30, "totalDistance": 8_000, "payment": 1_400},
                    "subPath": [
                        {"trafficType": 3, "distance": 200, "sectionTime": 3},
                        {
                            "trafficType": 1,
                            "distance": 7_600,
                            "sectionTime": 24,
                            "startName": "서울역",
                            "endName": "강남역",
                            "lane": [{"name": "2호선"}],
                        },
                    ],
                },
            ]
        }
    }

    route = parse_odsay_subway_route(payload)

    assert route.total_time_seconds == 30 * 60
    assert route.station_keys == (
        SubwayStationKey(line_name="2호선", station_name="서울"),
        SubwayStationKey(line_name="2호선", station_name="강남"),
    )


def test_odsay_subway_route_client_sends_expected_request_without_logging_api_key() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json=_odsay_payload())

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OdsaySubwayRouteClient(api_key="test-odsay-key", http_client=http_client)

    route = client.get_subway_route(
        origin=Location(name="서울시청", latitude=37.5666103, longitude=126.9783882),
        destination=Location(name="강남역", latitude=37.497952, longitude=127.027619),
    )

    assert route.total_time_seconds == 37 * 60
    assert captured_request is not None
    assert captured_request.url.path == "/v1/api/searchPubTransPathT"
    query = dict(captured_request.url.params)
    assert query["SX"] == "126.9783882"
    assert query["SY"] == "37.5666103"
    assert query["EX"] == "127.027619"
    assert query["EY"] == "37.497952"
    assert query["SearchType"] == "0"
    assert query["SearchPathType"] == "1"
    assert query["apiKey"] == "test-odsay-key"


def test_odsay_subway_route_client_converts_invalid_json_to_odsay_route_error() -> None:
    http_client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html>error</html>")))
    client = OdsaySubwayRouteClient(api_key="test-odsay-key", http_client=http_client)

    with pytest.raises(OdsayRouteError) as exc_info:
        client.get_subway_route(
            origin=Location(latitude=37.5666103, longitude=126.9783882),
            destination=Location(latitude=37.497952, longitude=127.027619),
        )

    assert exc_info.value.reason == "invalid_json"


def test_odsay_subway_route_client_converts_application_error_to_odsay_route_error() -> None:
    http_client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"error": {"code": "401"}})))
    client = OdsaySubwayRouteClient(api_key="test-odsay-key", http_client=http_client)

    with pytest.raises(OdsayRouteError) as exc_info:
        client.get_subway_route(
            origin=Location(latitude=37.5666103, longitude=126.9783882),
            destination=Location(latitude=37.497952, longitude=127.027619),
        )

    assert exc_info.value.reason == "odsay_api_error"


class DictAccessibilityProvider:
    def __init__(self, values: dict[SubwayStationKey, StationAccessibility]) -> None:
        self.values = values
        self.checked_keys: list[SubwayStationKey] = []

    def get_station_accessibility(self, station_key: SubwayStationKey) -> StationAccessibility | None:
        self.checked_keys.append(station_key)
        return self.values.get(station_key)


def test_build_accessibility_warnings_checks_origin_transfer_and_destination_stations() -> None:
    station_keys = (
        SubwayStationKey("1호선", "서울"),
        SubwayStationKey("1호선", "시청"),
        SubwayStationKey("2호선", "시청"),
        SubwayStationKey("2호선", "강남"),
    )
    provider = DictAccessibilityProvider(
        {
            station_keys[0]: StationAccessibility(has_operating_elevator=True, elevator_count=4),
            station_keys[1]: StationAccessibility(has_operating_elevator=True, elevator_count=3),
            station_keys[2]: StationAccessibility(has_operating_elevator=False, elevator_count=0),
            station_keys[3]: StationAccessibility(has_operating_elevator=True, elevator_count=4),
        }
    )

    warnings = build_accessibility_warnings(station_keys, provider)

    assert provider.checked_keys == list(station_keys)
    assert any("2호선 시청" in warning for warning in warnings)
    assert any("실시간 엘리베이터" in warning for warning in warnings)


def test_csv_subway_accessibility_provider_loads_analysis_station_master(tmp_path) -> None:
    csv_path = tmp_path / "station_accessibility_master.csv"
    csv_path.write_text(
        "\ufeff노선명,역명정규화,운행엘리베이터보유여부,운행엘리베이터수,엘리베이터설치위치,엘리베이터연결층\n"
        "1호선,서울,1,4,1번 출구,B1~1F\n"
        "2호선,시청,0,0,,\n",
        encoding="utf-8",
    )
    provider = CsvSubwayAccessibilityProvider(csv_path=csv_path)

    seoul = provider.get_station_accessibility(SubwayStationKey("서울 1호선", "서울역"))
    city_hall = provider.get_station_accessibility(SubwayStationKey("2호선", "시청"))

    assert seoul == StationAccessibility(
        has_operating_elevator=True,
        elevator_count=4,
        elevator_location="1번 출구",
        elevator_floor_connection="B1~1F",
    )
    assert city_hall == StationAccessibility(has_operating_elevator=False, elevator_count=0)


def test_csv_subway_accessibility_provider_requires_existing_master(tmp_path) -> None:
    with pytest.raises(OdsayRouteError) as exc_info:
        CsvSubwayAccessibilityProvider(csv_path=tmp_path / "missing.csv")

    assert exc_info.value.reason == "missing_accessibility_master"
