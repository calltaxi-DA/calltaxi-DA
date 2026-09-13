import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.hospital_analytics import HospitalAnalyticsError, load_hospital_analytics, resolve_hospital_chart


def test_hospital_analytics_returns_reviewed_export() -> None:
    response = TestClient(create_app()).get("/analytics/hospital")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_period"] == {
        "start_date": "2025-01-01", "end_date": "2025-12-31", "basis": "접수일시", "timezone": "Asia/Seoul"
    }
    assert [item["analysis_id"] for item in payload["analyses"]] == [
        "medical_destination_top_regions", "medical_trip_scope", "medical_trip_distance_coverage", "medical_net_flow_by_district"
    ]
    assert payload["analyses"][1]["values"]["same_district"]["count"] == 52_921


def test_hospital_chart_returns_reviewed_png() -> None:
    response = TestClient(create_app()).get("/analytics/hospital/charts/medical_within_5km_coverage")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_unknown_hospital_chart_does_not_resolve_arbitrary_path() -> None:
    response = TestClient(create_app()).get("/analytics/hospital/charts/not-reviewed")
    assert response.status_code == 404


def test_invalid_hospital_export_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "hospital.json"
    path.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
    with pytest.raises(HospitalAnalyticsError):
        load_hospital_analytics(path)


def test_missing_hospital_chart_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(HospitalAnalyticsError):
        resolve_hospital_chart("medical_within_5km_coverage", tmp_path)
