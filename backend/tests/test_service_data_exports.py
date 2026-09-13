import json
from pathlib import Path

from app.services.bus import (
    DEFAULT_LOW_FLOOR_BUS_ROUTE_MASTER_PATH,
    DEFAULT_ODSAY_BUS_ROUTE_MAPPING_PATH,
    CsvLowFloorBusRouteProvider,
)
from app.services.subway import DEFAULT_SUBWAY_ACCESSIBILITY_MASTER_PATH, CsvSubwayAccessibilityProvider


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "analysis/service_data_manifest.json"


def test_service_data_manifest_references_available_reviewed_exports() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    service_exports = {item["path"]: item for item in manifest["service_exports"]}
    expected_service_exports = {
        DEFAULT_SUBWAY_ACCESSIBILITY_MASTER_PATH: "backend subway accessibility provider",
        DEFAULT_LOW_FLOOR_BUS_ROUTE_MASTER_PATH: "backend low-floor bus provider",
        DEFAULT_ODSAY_BUS_ROUTE_MAPPING_PATH: "backend ODsay bus route provider",
        REPOSITORY_ROOT
        / "analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib": "ai waiting-time adapter",
        REPOSITORY_ROOT
        / "analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final_metadata.json": "ai waiting-time adapter",
        REPOSITORY_ROOT
        / "analysis/waiting_time/rf_v2_prev_day_weather_serving_feature_mapping.md": "ai waiting-time adapter",
    }

    assert manifest["schema_version"] == "1.1"
    assert {item["domain"] for item in manifest["service_exports"]} == {
        "subway",
        "low_floor_bus",
        "waiting_time",
    }
    assert set(service_exports) == {
        str(path.relative_to(REPOSITORY_ROOT)) for path in expected_service_exports
    }
    for path, consumer in expected_service_exports.items():
        item = service_exports[str(path.relative_to(REPOSITORY_ROOT))]
        assert item["status"] == "available"
        assert item["consumer"] == consumer
        assert path.is_file()

    reviewed_exports = {item["path"]: item for item in manifest["reviewed_analysis_exports"]}
    assert {item["domain"] for item in reviewed_exports.values()} == {"hospital"}
    assert all(item["status"] == "reviewed_not_served" for item in reviewed_exports.values())
    assert all("consumer" not in item for item in reviewed_exports.values())
    assert all((REPOSITORY_ROOT / path).is_file() for path in reviewed_exports)

    hospital_export = json.loads(
        (REPOSITORY_ROOT / "analysis/hospital/hospital_analytics.json").read_text(encoding="utf-8")
    )
    chart_paths = {chart["asset_path"] for chart in hospital_export["charts"]}
    reviewed_png_paths = {
        path for path, item in reviewed_exports.items() if item["format"] == "png"
    }
    assert chart_paths == reviewed_png_paths

    assert reviewed_exports["analysis/hospital/hospital_analytics.json"]["source_period"] == "2025"
    assert service_exports["analysis/subway/station_accessibility_master.csv"]["source_period"] == "2025-12"
    assert service_exports["analysis/bus/low_floor_bus_route_master.csv"]["source_period"] == "2025"


def test_reviewed_exports_load_outside_repository_working_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    subway_provider = CsvSubwayAccessibilityProvider()
    bus_provider = CsvLowFloorBusRouteProvider()

    assert subway_provider._lookup
    assert bus_provider._lookup
