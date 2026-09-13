import json
from pathlib import Path

from app.services.bus import CsvLowFloorBusRouteProvider
from app.services.hospital_analytics import load_hospital_analytics
from app.services.subway import CsvSubwayAccessibilityProvider


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "analysis/service_data_manifest.json"


def test_service_data_manifest_references_available_reviewed_exports() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == "1.0"
    assert {item["domain"] for item in manifest["exports"]} == {
        "hospital",
        "subway",
        "low_floor_bus",
    }
    for item in manifest["exports"]:
        assert item["status"] == "available"
        assert (REPOSITORY_ROOT / item["path"]).is_file()
    for asset in manifest["frontend_assets"]:
        assert (REPOSITORY_ROOT / asset["path"]).is_file()
        assert asset["served_by"].startswith("/analytics/hospital/charts/")


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
