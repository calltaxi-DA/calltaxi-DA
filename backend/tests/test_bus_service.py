import httpx
import pytest

from app.api.contracts import Location
from app.services.bus import (
    CsvLowFloorBusRouteProvider,
    LowFloorBusRouteEntry,
    LowFloorBusRouteUnavailableError,
    OdsayBusRouteError,
    OdsayLowFloorBusRouteClient,
    normalize_route_number,
    parse_odsay_low_floor_bus_route,
)


class DictRouteProvider:
    def __init__(self, statuses: dict[str, str]) -> None:
        lane_identity = {"999": (1, 11), "7016": (2, 12), "N31": (3, 11)}
        self.entries = {
            bus_id: LowFloorBusRouteEntry(
                odsay_bus_id=bus_id,
                odsay_bus_type=bus_type,
                route_number=route_number,
                route_number_normalized=normalize_route_number(route_number),
                accessibility_status=status,
            )
            for route_number, status in statuses.items()
            for bus_id, bus_type in [lane_identity[normalize_route_number(route_number)]]
        }

    def get_route(self, bus_id: int, route_number: str, bus_type: int) -> LowFloorBusRouteEntry | None:
        entry = self.entries.get(bus_id)
        if entry is None or entry.route_number_normalized != normalize_route_number(route_number):
            return None
        return entry if entry.odsay_bus_type == bus_type else None


def _odsay_bus_payload() -> dict:
    return {
        "result": {
            "path": [
                {
                    "pathType": 2,
                    "info": {"totalTime": 42, "totalDistance": 11_400, "payment": 1_500},
                    "subPath": [
                        {"trafficType": 3, "distance": 310, "sectionTime": 5},
                        {
                            "trafficType": 2,
                            "distance": 4_700,
                            "sectionTime": 15,
                            "startName": "서울역버스환승센터",
                            "endName": "광화문",
                            "lane": [
                                {"busNo": "999", "busID": 1, "type": 11},
                                {"busNo": " 7016 ", "busID": 2, "type": 12},
                            ],
                        },
                        {"trafficType": 3, "distance": 140, "sectionTime": 3},
                        {
                            "trafficType": 2,
                            "distance": 5_920,
                            "sectionTime": 15,
                            "startName": "광화문",
                            "endName": "강남역",
                            "lane": [{"busNo": "N31", "busID": 3, "type": 11}],
                        },
                        {"trafficType": 3, "distance": 330, "sectionTime": 4},
                    ],
                }
            ]
        }
    }


def test_parse_bus_route_matches_each_bus_section_and_sums_all_walking_sections() -> None:
    provider = DictRouteProvider({"999": "unavailable", "7016": "available", "N31": "available"})

    route = parse_odsay_low_floor_bus_route(_odsay_bus_payload(), provider)

    assert route.total_time_seconds == 42 * 60
    assert route.total_distance_meters == 11_400
    assert route.walking_distance_meters == 310 + 140 + 330
    assert route.walking_time_seconds == (5 + 3 + 4) * 60
    assert route.fare_won == 1_500
    assert [lane.route_number_normalized for lane in route.selected_lanes] == ["7016", "N31"]
    assert route.summary == "7016 → N31 저상버스 경로"


def test_parse_bus_route_uses_later_path_when_first_path_has_no_accessible_lane() -> None:
    payload = _odsay_bus_payload()
    inaccessible_path = payload["result"]["path"][0]
    accessible_path = {**inaccessible_path, "subPath": [dict(section) for section in inaccessible_path["subPath"]]}
    accessible_path["subPath"][1] = {
        **accessible_path["subPath"][1],
        "lane": [{"busNo": "7016", "busID": 2, "type": 12}],
    }
    inaccessible_path["subPath"][1]["lane"] = [{"busNo": "999", "busID": 1, "type": 11}]
    payload["result"]["path"] = [inaccessible_path, accessible_path]
    provider = DictRouteProvider({"7016": "available", "N31": "available"})

    route = parse_odsay_low_floor_bus_route(payload, provider)

    assert [lane.route_number_normalized for lane in route.selected_lanes] == ["7016", "N31"]


def test_parse_bus_route_rounds_decimal_distance_fields_to_contract_meters() -> None:
    payload = _odsay_bus_payload()
    payload["result"]["path"][0]["info"]["totalDistance"] = "11400.4"
    payload["result"]["path"][0]["subPath"][0]["distance"] = 310.6

    route = parse_odsay_low_floor_bus_route(
        payload,
        DictRouteProvider({"7016": "available", "N31": "available"}),
    )

    assert route.total_distance_meters == 11_400
    assert route.walking_distance_meters == 311 + 140 + 330


def test_parse_bus_route_rejects_path_with_unknown_or_unavailable_segment() -> None:
    provider = DictRouteProvider({"7016": "available", "N31": "unknown", "999": "unavailable"})

    with pytest.raises(LowFloorBusRouteUnavailableError):
        parse_odsay_low_floor_bus_route(_odsay_bus_payload(), provider)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("distance", None),
        ("sectionTime", None),
        ("distance", -1),
        ("sectionTime", -1),
        ("distance", "invalid"),
        ("sectionTime", "invalid"),
        ("distance", "300"),
        ("sectionTime", "5"),
        ("distance", float("nan")),
        ("distance", float("inf")),
        ("sectionTime", float("nan")),
        ("sectionTime", float("inf")),
    ],
)
@pytest.mark.parametrize("walking_section_index", [0, 2, 4])
def test_parse_bus_route_rejects_invalid_field_in_any_walking_section(
    walking_section_index: int,
    field_name: str,
    invalid_value: object,
) -> None:
    payload = _odsay_bus_payload()
    section = payload["result"]["path"][0]["subPath"][walking_section_index]
    if invalid_value is None:
        section.pop(field_name)
    else:
        section[field_name] = invalid_value

    with pytest.raises(OdsayBusRouteError):
        parse_odsay_low_floor_bus_route(payload, DictRouteProvider({"7016": "available", "N31": "available"}))


@pytest.mark.parametrize(
    "lane",
    [
        {"busNo": "7016", "busID": 9999, "type": 12},
        {"busNo": "7016", "busID": 2, "type": 1},
        {"busNo": "7016", "busID": 2},
        {"busNo": "7016", "type": 12},
    ],
)
def test_parse_bus_route_rejects_unreviewed_or_mismatched_lane_identity(lane: dict) -> None:
    payload = _odsay_bus_payload()
    payload["result"]["path"][0]["subPath"][1]["lane"] = [lane]

    with pytest.raises(LowFloorBusRouteUnavailableError):
        parse_odsay_low_floor_bus_route(payload, DictRouteProvider({"7016": "available", "N31": "available"}))


def test_parse_bus_route_does_not_accept_bus_and_subway_mixed_path() -> None:
    payload = _odsay_bus_payload()
    payload["result"]["path"][0]["subPath"].insert(2, {"trafficType": 1, "distance": 1000, "sectionTime": 3})

    with pytest.raises(LowFloorBusRouteUnavailableError):
        parse_odsay_low_floor_bus_route(payload, DictRouteProvider({"7016": "available", "N31": "available"}))


def test_odsay_bus_client_sends_bus_only_search_parameters() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json=_odsay_bus_payload())

    client = OdsayLowFloorBusRouteClient(
        api_key="test-key",
        route_provider=DictRouteProvider({"7016": "available", "N31": "available"}),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client.get_low_floor_bus_route(
        Location(latitude=37.5666, longitude=126.9784),
        Location(latitude=37.4979, longitude=127.0276),
    )

    assert captured_request is not None
    query = dict(captured_request.url.params)
    assert captured_request.url.path == "/v1/api/searchPubTransPathT"
    assert query["SearchType"] == "0"
    assert query["SearchPathType"] == "2"
    assert query["apiKey"] == "test-key"


def test_odsay_bus_client_converts_application_error() -> None:
    client = OdsayLowFloorBusRouteClient(
        api_key="test-key",
        route_provider=DictRouteProvider({}),
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"error": {"code": "500"}}))
        ),
    )

    with pytest.raises(OdsayBusRouteError) as exc_info:
        client.get_low_floor_bus_route(
            Location(latitude=37.5666, longitude=126.9784),
            Location(latitude=37.4979, longitude=127.0276),
        )

    assert exc_info.value.reason == "odsay_api_error"


def test_csv_route_provider_loads_reviewed_analysis_export(tmp_path) -> None:
    csv_path = tmp_path / "routes.csv"
    csv_path.write_text(
        "route_number,route_number_normalized,accessibility_status\n"
        "0017,0017,available\n"
        "N31,N31,unknown\n",
        encoding="utf-8",
    )

    mapping_path = tmp_path / "mapping.csv"
    mapping_path.write_text(
        "odsay_bus_id,odsay_bus_no,odsay_bus_type,route_number_normalized\n"
        "17,0017,12,0017\n"
        "31,N31,11,N31\n",
        encoding="utf-8",
    )
    provider = CsvLowFloorBusRouteProvider(csv_path, mapping_path)

    assert provider.get_route(17, " 0017 ", 12) == LowFloorBusRouteEntry(17, 12, "0017", "0017", "available")
    assert provider.get_route(31, "n31", 11) == LowFloorBusRouteEntry(31, 11, "N31", "N31", "unknown")
    assert provider.get_route(17, "17", 12) is None
    assert provider.get_route(17, "0017", 1) is None


def test_csv_route_provider_rejects_duplicate_normalized_route_number(tmp_path) -> None:
    csv_path = tmp_path / "routes.csv"
    csv_path.write_text(
        "route_number,route_number_normalized,accessibility_status\n"
        "7016,7016,available\n"
        " 7016 ,7016,available\n",
        encoding="utf-8",
    )

    with pytest.raises(OdsayBusRouteError) as exc_info:
        CsvLowFloorBusRouteProvider(csv_path, tmp_path / "unused.csv")

    assert exc_info.value.reason == "duplicate_route_number"
