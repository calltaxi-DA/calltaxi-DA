from pathlib import Path

import pytest

from src.data_quality import Audit, BUS, MAPPING, SUBWAY, audit_exports, compare_report, profile, read_csv, validate_bus, validate_subway

ROOT = Path(__file__).resolve().parents[2]


def test_reviewed_exports_match_committed_hospital_sources() -> None:
    report = audit_exports(ROOT)
    assert not report.errors
    assert report.metrics["hospital_source_comparison"]["district_top5"]["count_sum"] == 126705
    assert report.metrics["hospital_notebook_evidence"]["charts_compared"] == 2


def test_missing_original_sources_are_explicitly_unverified(tmp_path: Path) -> None:
    report = audit_exports(ROOT, tmp_path)
    assert not report.errors
    assert sum(item.get("status") == "not_verified_source_missing" for item in report.metrics.values() if isinstance(item, dict)) == 3


def test_check_report_detects_committed_export_drift(tmp_path: Path) -> None:
    report = audit_exports(ROOT, tmp_path)
    expected = tmp_path / "audit.json"
    expected.write_text('{"metrics": {"analysis/bus/low_floor_bus_route_master.csv": {"rows": 999}}, "errors": []}', encoding="utf-8")
    assert "report drift: metrics.analysis/bus/low_floor_bus_route_master.csv" in compare_report(report, expected)


def test_profile_counts_nulls_and_duplicate_keys_separately() -> None:
    result = profile([{"id": "1", "value": ""}, {"id": "1", "value": "3"}], ("id",))
    assert result["duplicate_keys"] == 1
    assert result["duplicate_rows"] == 0
    assert result["missing"]["value"] == 1


def test_csv_rejects_truncated_rows(tmp_path: Path) -> None:
    path = tmp_path / "broken.csv"
    path.write_text("id,value\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="row width"):
        read_csv(path)


@pytest.mark.parametrize("column,value", [("운행엘리베이터보유여부", ""), ("운행엘리베이터수", "-1"), ("station_key", "wrong"), ("사용월", "2026-12")])
def test_subway_rejects_missing_invalid_and_inconsistent_values(column: str, value: str) -> None:
    rows = read_csv(ROOT / SUBWAY)
    rows[0][column] = value
    report = Audit()
    validate_subway(rows, report)
    assert report.errors


@pytest.mark.parametrize("column,value", [("accessibility_status", "unknown"), ("low_floor_bus_rate", "nan"), ("low_floor_bus_count", "-1")])
def test_bus_rejects_inconsistent_flags_and_nonfinite_metrics(column: str, value: str) -> None:
    rows = read_csv(ROOT / BUS)
    rows[0][column] = value
    report = Audit()
    validate_bus(rows, read_csv(ROOT / MAPPING), report)
    assert report.errors


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"low_floor_bus_count": "0", "has_low_floor_bus": "1"}, "low-floor flag/count mismatch"),
        ({"low_floor_bus_count": "", "has_low_floor_bus": "0", "accessibility_status": "unknown"}, "missing count must keep low-floor flag empty"),
        ({"congestion_data_available": "0", "congestion_row_count": "100"}, "unavailable congestion must have zero rows"),
        ({"congestion_data_available": "0", "max_low_floor_bus_load_per_bus": "30"}, "unavailable congestion must not keep proxy values"),
        ({"congestion_data_available": "1", "congestion_row_count": "0", "max_low_floor_bus_load_per_bus": "1", "p95_low_floor_bus_load_per_bus": "1"}, "available congestion must have rows"),
        ({"congestion_data_available": "1", "congestion_row_count": "1", "max_low_floor_bus_load_per_bus": "", "p95_low_floor_bus_load_per_bus": ""}, "available congestion must keep proxy values"),
    ],
)
def test_bus_rejects_internal_flag_value_contradictions(updates: dict[str, str], message: str) -> None:
    rows = read_csv(ROOT / BUS)
    target = next(row for row in rows if row["route_number_normalized"] == "01A")
    target.update(updates)
    report = Audit()
    validate_bus(rows, read_csv(ROOT / MAPPING), report)
    assert any(message in error for error in report.errors)


def test_mapping_rejects_dangling_reference() -> None:
    mapping = read_csv(ROOT / MAPPING)
    mapping[0]["route_number_normalized"] = "MISSING"
    report = Audit()
    validate_bus(read_csv(ROOT / BUS), mapping, report)
    assert "mapping references absent routes" in report.errors


def test_congestion_accepts_export_rounding_but_rejects_changed_value(tmp_path: Path) -> None:
    from src.data_quality import CONGESTION_SOURCE, compare_congestion

    source = tmp_path / CONGESTION_SOURCE
    source.parent.mkdir(parents=True)
    source.write_text("노선번호,저상버스1대당_추정재차인원\n5522A,23440.375\n", encoding="utf-8")
    master = [{"route_number_normalized": "5522A", "congestion_data_available": "1", "congestion_row_count": "1", "max_low_floor_bus_load_per_bus": "23440.38", "p95_low_floor_bus_load_per_bus": "23440.38"}]
    result = Audit()
    compare_congestion(tmp_path, master, result)
    assert not result.errors
    master[0]["max_low_floor_bus_load_per_bus"] = "23440.39"
    result = Audit()
    compare_congestion(tmp_path, master, result)
    assert result.errors


def test_linear_percentile_interpolation() -> None:
    from src.data_quality import percentile95

    assert percentile95([0, 100]) == 95
