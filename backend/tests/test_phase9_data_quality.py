"""Validate all reviewed lookup entries through the real service providers."""
import csv
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.bus import CsvLowFloorBusRouteProvider
from app.services.subway import CsvSubwayAccessibilityProvider, SubwayStationKey

ROOT = Path(__file__).resolve().parents[2]


def test_all_reviewed_subway_entries_match_provider() -> None:
    provider = CsvSubwayAccessibilityProvider()
    with (ROOT / "analysis/subway/station_accessibility_master.csv").open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 158
    for row in rows:
        result = provider.get_station_accessibility(SubwayStationKey(row["노선명"], row["역명"]))
        assert result is not None
        assert result.has_operating_elevator == (row["운행엘리베이터보유여부"] == "1")
        assert result.elevator_count == int(row["운행엘리베이터수"])
        assert result.elevator_location == row["엘리베이터설치위치"]
        assert result.elevator_floor_connection == row["엘리베이터연결층"]
    assert provider.get_station_accessibility(SubwayStationKey("없는노선", "서울역")) is None
    assert provider.get_station_accessibility(SubwayStationKey("1호선", "없는역")) is None


def test_all_reviewed_bus_lanes_match_and_id_number_type_mismatches_fail_closed() -> None:
    provider = CsvLowFloorBusRouteProvider()
    with (ROOT / "analysis/bus/odsay_seoul_bus_route_mapping.csv").open(encoding="utf-8-sig") as stream:
        mappings = list(csv.DictReader(stream))
    with (ROOT / "analysis/bus/low_floor_bus_route_master.csv").open(encoding="utf-8-sig") as stream:
        master = {row["route_number_normalized"]: row for row in csv.DictReader(stream)}
    assert len(mappings) == 51
    for row in mappings:
        bus_id, bus_type = int(row["odsay_bus_id"]), int(row["odsay_bus_type"])
        result = provider.get_route(bus_id, row["odsay_bus_no"], bus_type)
        assert result is not None
        assert result.accessibility_status == master[row["route_number_normalized"]]["accessibility_status"]
        assert provider.get_route(bus_id, "WRONG", bus_type) is None
        assert provider.get_route(bus_id, row["odsay_bus_no"], -1) is None
        assert provider.get_route(-1, row["odsay_bus_no"], bus_type) is None


def test_hospital_reviewed_data_remains_unserved() -> None:
    app = create_app()
    assert not any("hospital" in path for path in app.openapi()["paths"])
    client = TestClient(app)
    assert client.get("/hospital-analytics").status_code == 404
    assert client.get("/analysis/hospital/hospital_analytics.json").status_code == 404
    for path in (ROOT / "frontend/src").rglob("*.tsx"):
        if "__tests__" not in path.parts:
            assert "HospitalDestinationInsights" not in path.read_text(encoding="utf-8")
