import json
from pathlib import Path

from app.services.bus import (
    DEFAULT_LOW_FLOOR_BUS_ROUTE_MASTER_PATH,
    DEFAULT_ODSAY_BUS_ROUTE_MAPPING_PATH,
    CsvLowFloorBusRouteProvider,
)
from app.services.hospital_analytics import DEFAULT_HOSPITAL_ANALYTICS_PATH, load_hospital_analytics
from app.services.subway import DEFAULT_SUBWAY_ACCESSIBILITY_MASTER_PATH, CsvSubwayAccessibilityProvider


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "analysis/service_data_manifest.json"


def test_service_data_manifest_references_available_reviewed_exports() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    exports = {item["path"]: item for item in manifest["exports"]}
    expected_exports = {
        DEFAULT_HOSPITAL_ANALYTICS_PATH: "backend hospital analytics API",
        DEFAULT_SUBWAY_ACCESSIBILITY_MASTER_PATH: "backend subway accessibility provider",
        DEFAULT_LOW_FLOOR_BUS_ROUTE_MASTER_PATH: "backend low-floor bus provider",
        DEFAULT_ODSAY_BUS_ROUTE_MAPPING_PATH: "backend ODsay bus route provider",
    }

    assert manifest["schema_version"] == "1.0"
    assert {item["domain"] for item in manifest["exports"]} == {
        "hospital",
        "subway",
        "low_floor_bus",
    }
    assert set(exports) == {str(path.relative_to(REPOSITORY_ROOT)) for path in expected_exports}
    for path, consumer in expected_exports.items():
        item = exports[str(path.relative_to(REPOSITORY_ROOT))]
        assert item["status"] == "available"
        assert item["consumer"] == consumer
        assert path.is_file()

    analytics = load_hospital_analytics()
    chart_assets = {chart.asset_url for chart in analytics.charts}
    frontend_assets = {asset["served_by"] for asset in manifest["frontend_assets"]}
    assert frontend_assets == chart_assets
    for asset in manifest["frontend_assets"]:
        assert (REPOSITORY_ROOT / asset["path"]).is_file()

    assert exports["analysis/hospital/hospital_analytics.json"]["source_period"] == "2025"
    assert exports["analysis/subway/station_accessibility_master.csv"]["source_period"] == "2025-12"
    assert exports["analysis/bus/low_floor_bus_route_master.csv"]["source_period"] == "2025"


def test_reviewed_exports_load_outside_repository_working_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    analytics = load_hospital_analytics()
    subway_provider = CsvSubwayAccessibilityProvider()
    bus_provider = CsvLowFloorBusRouteProvider()

    assert len(analytics.analyses) == 4
    assert subway_provider._lookup
    assert bus_provider._lookup
