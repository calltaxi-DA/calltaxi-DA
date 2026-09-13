"""Read-only Phase 9 audit. Run: python -m src.data_quality [--source-root PATH].

Stdlib-only offline analysis; never imports service code or writes analysis exports.
Exit 1 denotes invalid exports; warnings identify explicitly unverified scope.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

SUBWAY = "analysis/subway/station_accessibility_master.csv"
BUS = "analysis/bus/low_floor_bus_route_master.csv"
MAPPING = "analysis/bus/odsay_seoul_bus_route_mapping.csv"
HOSPITAL = "analysis/hospital/hospital_analytics.json"
SUBWAY_SOURCE = "data/processed/서울교통공사_장애인_지하철_승하차인원_정제_20251231.csv"
BUS_SOURCE = "data/raw/bus/all_bus_routes.json"
CONGESTION_SOURCE = "data/processed/bus/버스_저상노선_시간대별_추정재차인원_혼잡도_2025.csv"


@dataclass
class Audit:
    metrics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def check(self, valid: bool, message: str) -> None:
        if not valid:
            self.errors.append(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("missing or duplicate CSV headers")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("CSV row width differs from header")
    return rows


def profile(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[str, Any]:
    columns = list(rows[0]) if rows else []
    return {
        "rows": len(rows),
        "duplicate_rows": len(rows) - len({tuple(row.items()) for row in rows}),
        "duplicate_keys": len(rows) - len({tuple(row.get(k, "") for k in keys) for row in rows}),
        "missing": {key: sum(not row[key].strip() for row in rows) for key in columns},
    }


def normalized(value: str) -> str:
    return "".join(value.split()).upper()


def nonnegative(value: str) -> bool:
    try:
        number = float(value)
        return math.isfinite(number) and number >= 0
    except ValueError:
        return False


def audit_exports(root: Path, source_root: Path | None = None) -> Audit:
    audit = Audit()
    source_root = source_root or root
    tables: dict[str, list[dict[str, str]]] = {}
    specifications = {
        SUBWAY: ("station_key",), BUS: ("route_number_normalized",), MAPPING: ("odsay_bus_id",),
    }
    for path, keys in specifications.items():
        try:
            rows = read_csv(root / path)
            tables[path] = rows
            stats = profile(rows, keys)
            stats["sha256"] = hashlib.sha256((root / path).read_bytes()).hexdigest()
            audit.metrics[path] = stats
            audit.check(bool(rows), f"{path}: empty table")
            audit.check(stats["duplicate_keys"] == 0, f"{path}: duplicate key")
            audit.check(stats["duplicate_rows"] == 0, f"{path}: duplicate row")
            audit.check(all(all(row.get(key, "").strip() for key in keys) for row in rows), f"{path}: missing key")
        except (OSError, ValueError) as exc:
            audit.errors.append(f"{path}: {type(exc).__name__}: {exc}")
    if len(tables) != len(specifications):
        return audit
    checks = [
        ("subway", lambda: validate_subway(tables[SUBWAY], audit)),
        ("bus", lambda: validate_bus(tables[BUS], tables[MAPPING], audit)),
        ("hospital", lambda: validate_hospital(root, audit)),
        ("notebook evidence", lambda: validate_notebook_evidence(root, audit)),
        ("source comparison", lambda: compare_sources(root, source_root, tables, audit)),
        ("congestion", lambda: compare_congestion(source_root, tables[BUS], audit)),
    ]
    for name, check in checks:
        try:
            check()
        except (KeyError, ValueError, TypeError, OSError) as exc:
            audit.errors.append(f"{name}: invalid source/schema: {type(exc).__name__}: {exc}")
    return audit


def validate_subway(rows: list[dict[str, str]], audit: Audit) -> None:
    for row in rows:
        key = row["station_key"]
        audit.check(key == f'{row["노선명"]}|{row["역명정규화"]}', f"subway {key}: inconsistent canonical key")
        for column, value in row.items():
            if column.endswith("보유여부"):
                audit.check(value in {"0", "1"}, f"subway {key}: invalid {column}")
            if column.endswith("수"):
                audit.check(value.isdigit(), f"subway {key}: invalid count {column}")
        count = int(row["운행엘리베이터수"])
        audit.check((count > 0) == (row["운행엘리베이터보유여부"] == "1"), f"subway {key}: elevator flag/count mismatch")
        audit.check(bool(row["엘리베이터설치위치"].strip()) and bool(row["엘리베이터연결층"].strip()), f"subway {key}: missing elevator details")
    audit.metrics["subway_periods"] = sorted({row["사용월"] for row in rows})
    audit.check(audit.metrics["subway_periods"] == ["2025-12"], "subway: reviewed month changed; re-review provenance")
    audit.warnings.append("Subway usage month is not the collection date of facilities; live outages and full ODsay station coverage remain unverified.")


def validate_bus(rows: list[dict[str, str]], mapping: list[dict[str, str]], audit: Audit) -> None:
    routes = {row["route_number_normalized"]: row for row in rows}
    for row in rows:
        key = row["route_number_normalized"]
        audit.check(normalized(row["route_number"]) == key, f"bus {key}: inconsistent canonical key")
        value = row["low_floor_bus_count"]
        expected = "unknown" if not value else "available" if float(value) > 0 else "unavailable"
        audit.check(row["accessibility_status"] == expected, f"bus {key}: inconsistent accessibility status")
        if value:
            audit.check(nonnegative(value) and float(value).is_integer(), f"bus {key}: invalid low-floor count")
            audit.check(nonnegative(row["authorized_bus_count"]) and float(value) <= float(row["authorized_bus_count"]), f"bus {key}: invalid authorized count")
            rate = float(row["low_floor_bus_rate"])
            audit.check(math.isfinite(rate) and 0 <= rate <= 1, f"bus {key}: invalid low-floor rate")
        else:
            audit.warnings.append(f"Bus {key}: low-floor metadata missing; unknown must remain excluded.")
        for column in ("stop_count", "congestion_row_count"):
            audit.check(row[column].isdigit(), f"bus {key}: invalid {column}")
        for column in ("max_low_floor_bus_load_per_bus", "p95_low_floor_bus_load_per_bus"):
            if row["congestion_data_available"] == "1":
                audit.check(nonnegative(row[column]), f"bus {key}: invalid congestion proxy")
    unmapped = []
    for row in mapping:
        key = row["route_number_normalized"]
        audit.check(row["odsay_bus_id"].isdigit() and int(row["odsay_bus_id"]) > 0, f"mapping {key}: invalid ID")
        audit.check(row["odsay_bus_type"].isdigit(), f"mapping {key}: invalid type")
        audit.check(normalized(row["odsay_bus_no"]) == key, f"mapping {key}: number mismatch")
        if key not in routes:
            unmapped.append(key)
        date.fromisoformat(row["validation_date"])
        audit.check(bool(row["evidence"].strip()), f"mapping {key}: missing evidence")
    audit.check(not unmapped, "mapping references absent routes")
    audit.metrics["bus_mapping"] = {
        "missing_route_references": unmapped,
        "mapped_master_routes": len({row["route_number_normalized"] for row in mapping} & routes.keys()),
        "master_routes_without_mapping": sorted(routes.keys() - {row["route_number_normalized"] for row in mapping}),
        "validation_dates": sorted({row["validation_date"] for row in mapping}),
        "accessibility_status_counts": dict(Counter(row["accessibility_status"] for row in rows)),
        "metadata_dates": dict(Counter(row["route_metadata_as_of"] for row in rows)),
        "ridership_years": sorted({row["ridership_basis_year"] for row in rows}),
    }
    audit.check(audit.metrics["bus_mapping"]["ridership_years"] == ["2025"], "bus: reviewed ridership year changed; re-review provenance")
    for row in rows:
        if row["route_metadata_as_of"] != "unknown":
            date.fromisoformat(row["route_metadata_as_of"])
    audit.warnings.append("Bus metadata date is unknown; 2025 ridership and 2026-09-12 mapping validation dates do not date the fleet snapshot.")
    audit.warnings.append("Export mapping coverage is not a live route success rate; excluded historical ODsay lanes are not stored in the reviewed mapping.")


def validate_hospital(root: Path, audit: Audit) -> None:
    data = json.loads((root / HOSPITAL).read_text(encoding="utf-8"))
    analyses = {item["analysis_id"]: item for item in data["analyses"]}
    audit.check(len(analyses) == len(data["analyses"]) == 4, "hospital: duplicate/missing analysis IDs")
    audit.check(data["source_period"] == {"start_date": "2025-01-01", "end_date": "2025-12-31", "basis": "접수일시", "timezone": "Asia/Seoul"}, "hospital: period mismatch")
    for item in analyses.values():
        audit.check(all(item.get(k) for k in ("population_definition", "aggregation_unit", "limitations", "values")), "hospital: missing interpretation metadata")
    scope = analyses["medical_trip_scope"]["values"]
    audit.check(sum(item["count"] for item in scope.values()) == 126561, "hospital: distance population mismatch")
    for item in scope.values():
        audit.check(round(item["count"] / 126561 * 100, 1) == item["percentage"], "hospital: scope percentage mismatch")
    comparisons = {}
    for level, filename, fields in [
        ("district_top5", "region_gu_call_hospital_combined_medical.csv", ("목적구",)),
        ("neighborhood_top5", "region_dong_call_hospital_combined_medical.csv", ("목적구", "행정동")),
    ]:
        rows = read_csv(root / "data/processed" / filename)
        stats = profile(rows, fields)
        audit.check(stats["duplicate_keys"] == 0, f"hospital {level}: duplicate source key")
        audit.check(all(all(row.get(key, "").strip() for key in (*fields, "콜택시_의료목적지_건수")) for row in rows), f"hospital {level}: missing source value")
        top = sorted(rows, key=lambda row: int(row["콜택시_의료목적지_건수"]), reverse=True)[:5]
        actual = [{"name": row[fields[-1]], "count": int(row["콜택시_의료목적지_건수"]), **({"district": row["목적구"]} if len(fields) == 2 else {})} for row in top]
        audit.check(actual == analyses["medical_destination_top_regions"]["values"][level], f"hospital {level}: source/export mismatch")
        comparisons[level] = {**stats, "count_sum": sum(int(row["콜택시_의료목적지_건수"]) for row in rows)}
    audit.check(comparisons["district_top5"]["count_sum"] == 126705, "hospital: destination population mismatch")
    audit.metrics["hospital_source_comparison"] = comparisons
    for chart in data["charts"]:
        image = root / chart["asset_path"]
        audit.check(image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "hospital: invalid PNG")
        audit.check(set(chart["analysis_ids"]) <= analyses.keys(), "hospital: orphan chart analysis")
    audit.metrics[HOSPITAL] = {"sha256": hashlib.sha256((root / HOSPITAL).read_bytes()).hexdigest(), "analyses": len(analyses), "source_period": data["source_period"]}



def notebook_output(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    parts = []
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            text = output.get("text", output.get("data", {}).get("text/plain", []))
            parts.append("".join(text) if isinstance(text, list) else text)
    return "\n".join(parts)


def validate_notebook_evidence(root: Path, audit: Audit) -> None:
    data = json.loads((root / HOSPITAL).read_text(encoding="utf-8"))
    values = {item["analysis_id"]: item["values"] for item in data["analyses"]}
    distance = root / "notebooks_region_facilities/04_3_medical_trip_distance_analysis.ipynb"
    flow = root / "notebooks_region_facilities/07_2_medical_destination_analysis_and_insights.ipynb"
    text = notebook_output(distance)
    for label, key in (("같은구", "same_district"), ("다른구", "different_district")):
        match = re.search(rf"의료목적콜 {label} 이동: ([\d,]+)건 \(([\d.]+)%\)", text)
        audit.check(match is not None, f"hospital notebook: missing {label} scope evidence")
        if match:
            expected = values["medical_trip_scope"][key]
            audit.check(int(match[1].replace(",", "")) == expected["count"] and float(match[2]) == expected["percentage"], f"hospital notebook: {label} scope mismatch")
    for label, key in (("같은구", "same_district"), ("다른구", "different_district"), ("전체", "overall")):
        match = re.search(rf"^\s*{label}\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s*$", text, re.MULTILINE)
        audit.check(match is not None, f"hospital notebook: missing {label} coverage evidence")
        if match:
            audit.check(round(float(match[1]), 1) == values["medical_trip_distance_coverage"][f"{key}_within_5km_percentage"], f"hospital notebook: {label} coverage mismatch")
    text = notebook_output(flow)
    for group in values["medical_net_flow_by_district"].values():
        for item in group:
            match = re.search(rf"^\d+\s+{re.escape(item['name'])}\s+\d+\s+\d+\s+(-?\d+)\s+\d+\s*$", text, re.MULTILINE)
            audit.check(match is not None and int(match[1]) == item["count"], f"hospital notebook: net flow mismatch {item['name']}")
    images = {
        "medical_same_vs_different_district.png": "fig1_04_3_same_vs_diff_ratio_medical_vs_all.png",
        "medical_within_5km_coverage.png": "fig2_04_3_5km_coverage_medical.png",
    }
    for target, source in images.items():
        audit.check((root / "analysis/hospital/figures" / target).read_bytes() == (root / "notebooks_region_facilities/outputs" / source).read_bytes(), f"hospital image differs from reviewed source: {target}")
    audit.metrics["hospital_notebook_evidence"] = {
        "comparison": "stored outputs only; notebooks not executed",
        "notebook_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (distance, flow)},
        "charts_compared": len(images),
    }


def compare_sources(root: Path, source_root: Path, tables: dict[str, list[dict[str, str]]], audit: Audit) -> None:
    for filename in (SUBWAY_SOURCE, BUS_SOURCE):
        path = source_root / filename
        if not path.is_file():
            audit.metrics[filename] = {"status": "not_verified_source_missing"}
            audit.warnings.append(f"{filename}: original source unavailable; no source consistency claim.")
            continue
        mismatches = 0
        if filename == SUBWAY_SOURCE:
            rows = read_csv(path)
            for source_row in rows:
                source_row["역명정규화"] = source_row["역명"].strip().replace(" ", "").removesuffix("역")
            latest = max(row["사용월"] for row in rows)
            selected = [row for row in rows if row["사용월"] == latest]
            lookup = {(row["노선명"], row["역명정규화"]): row for row in selected}
            audit.check(len(lookup) == len(selected), "subway source: duplicate latest-month key")
            for row in tables[SUBWAY]:
                original = lookup.get((row["노선명"], row["역명정규화"]))
                mismatches += int(original is None or any(original.get(k) != v for k, v in row.items() if k != "station_key"))
            audit.check(len(selected) == len(tables[SUBWAY]), "subway source/export count mismatch")
            details = {**profile(rows, ("사용월", "노선명", "역명정규화")), "latest_month": latest, "latest_rows": len(selected)}
        else:
            rows = json.loads(path.read_text(encoding="utf-8"))
            lookup = {normalized(row["number"]): row for row in rows}
            audit.check(len(rows) == len(lookup) == len(tables[BUS]), "bus source: duplicate key/count mismatch")
            pairs = {"seoul_route_id": "id", "route_type_code": "type", "endpoints": "endpoints", "authorized_bus_count": "authorized", "low_floor_bus_count": "low_count", "low_floor_bus_rate": "low_rate"}
            rounded_rates = 0
            for row in tables[BUS]:
                original = lookup.get(row["route_number_normalized"])
                if original is None:
                    mismatches += 1
                    continue
                differences = []
                for target, source in pairs.items():
                    value = original.get(source)
                    text = str(value if value is not None else "")
                    if target == "low_floor_bus_rate" and text and row[target]:
                        rounded_rates += int(text != row[target])
                        differences.append(abs(float(text) - float(row[target])) > 0.00005 + 1e-12)
                    else:
                        differences.append(text != row[target])
                mismatches += int(any(differences))
            details = {"rows": len(rows), "rates_rounded_to_4_decimals": rounded_rates}
        audit.check(mismatches == 0, f"{filename}: {mismatches} source/export mismatches")
        audit.metrics[filename] = {**details, "status": "passed" if mismatches == 0 else "failed", "mismatched_rows": mismatches, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * 0.95
    left = math.floor(position)
    right = math.ceil(position)
    return ordered[left] + (ordered[right] - ordered[left]) * (position - left)


def compare_congestion(source_root: Path, master: list[dict[str, str]], audit: Audit) -> None:
    path = source_root / CONGESTION_SOURCE
    if not path.exists():
        audit.metrics[CONGESTION_SOURCE] = {"status": "not_verified_source_missing"}
        audit.warnings.append("Congestion source unavailable; annual proxy aggregates not independently reproduced.")
        return
    groups: dict[str, list[float]] = defaultdict(list)
    missing = 0
    count = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            count += 1
            value = row["저상버스1대당_추정재차인원"]
            if not value or not nonnegative(value):
                missing += 1
                continue
            groups[normalized(row["노선번호"])].append(float(value))
    mismatched = []
    for row in master:
        values = groups.get(row["route_number_normalized"], [])
        if not values:
            valid = row["congestion_data_available"] == "0" and row["congestion_row_count"] == "0"
        else:
            valid = (row["congestion_data_available"] == "1"
                     and len(values) == int(row["congestion_row_count"])
                     and abs(max(values) - float(row["max_low_floor_bus_load_per_bus"])) <= 0.005 + 1e-9
                     and abs(percentile95(values) - float(row["p95_low_floor_bus_load_per_bus"])) <= 0.005 + 1e-9)
        if not valid:
            mismatched.append(row["route_number_normalized"])
    missing_routes = sorted(groups.keys() - {row["route_number_normalized"] for row in master})
    audit.check(missing == 0, "congestion source: missing/nonfinite/negative proxy")
    audit.check(not mismatched and not missing_routes, "congestion source/export aggregate mismatch")
    audit.metrics[CONGESTION_SOURCE] = {
        "status": "passed" if not missing and not mismatched and not missing_routes else "failed",
        "rows": count, "routes": len(groups), "invalid_proxy_rows": missing,
        "mismatched_routes": mismatched, "unmapped_routes": missing_routes,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "compared_fields": ["congestion_data_available", "congestion_row_count", "max_low_floor_bus_load_per_bus", "p95_low_floor_bus_load_per_bus"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    result = audit_exports(args.root, args.source_root)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return int(bool(result.errors))


if __name__ == "__main__":
    raise SystemExit(main())
