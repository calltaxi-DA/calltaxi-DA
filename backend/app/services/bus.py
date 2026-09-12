"""ODsay 버스 경로와 검토 완료된 저상버스 route master를 결합한다."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.api.contracts import Location

ODSAY_BUS_ROUTE_URL = "https://api.odsay.com/v1/api/searchPubTransPathT"
DEFAULT_LOW_FLOOR_BUS_ROUTE_MASTER_PATH = Path("analysis/bus/low_floor_bus_route_master.csv")
DEFAULT_ODSAY_BUS_ROUTE_MAPPING_PATH = Path("analysis/bus/odsay_seoul_bus_route_mapping.csv")
WALKING_TRAFFIC_TYPE = 3
BUS_TRAFFIC_TYPE = 2
BUS_PATH_TYPE = 2


class OdsayBusRouteError(RuntimeError):
    """ODsay 버스 경로 요청 또는 응답을 처리할 수 없을 때 발생한다."""

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class LowFloorBusRouteUnavailableError(RuntimeError):
    """ODsay 경로 중 저상버스 route master 조건을 만족하는 경로가 없을 때 발생한다."""


@dataclass(frozen=True)
class LowFloorBusRouteEntry:
    odsay_bus_id: int
    odsay_bus_type: int
    route_number: str
    route_number_normalized: str
    accessibility_status: str


@dataclass(frozen=True)
class SelectedBusLane:
    route_number: str
    route_number_normalized: str
    start_stop_name: str | None
    end_stop_name: str | None


@dataclass(frozen=True)
class LowFloorBusRouteMetrics:
    total_time_seconds: int
    total_distance_meters: int
    walking_distance_meters: int
    walking_time_seconds: int
    fare_won: int
    selected_lanes: tuple[SelectedBusLane, ...]
    summary: str


class LowFloorBusRouteProvider(Protocol):
    def get_route(self, bus_id: int, route_number: str, bus_type: int) -> LowFloorBusRouteEntry | None:
        ...


class CsvLowFloorBusRouteProvider:
    """검토 완료된 ODsay busID 매핑을 통해서만 서울 route master를 조회한다."""

    def __init__(
        self,
        csv_path: Path = DEFAULT_LOW_FLOOR_BUS_ROUTE_MASTER_PATH,
        mapping_path: Path = DEFAULT_ODSAY_BUS_ROUTE_MAPPING_PATH,
    ) -> None:
        self.csv_path = csv_path
        route_lookup = self._load_route_lookup(csv_path)
        self._lookup = self._load_mapping_lookup(mapping_path, route_lookup)

    def get_route(self, bus_id: int, route_number: str, bus_type: int) -> LowFloorBusRouteEntry | None:
        entry = self._lookup.get(bus_id)
        if entry is None:
            return None
        if entry.route_number_normalized != normalize_route_number(route_number):
            return None
        if entry.odsay_bus_type != bus_type:
            return None
        return entry

    @staticmethod
    def _load_route_lookup(csv_path: Path) -> dict[str, tuple[str, str]]:
        if not csv_path.exists():
            raise OdsayBusRouteError("low-floor bus route master is missing", reason="missing_route_master")

        lookup: dict[str, tuple[str, str]] = {}
        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            required_columns = {"route_number", "route_number_normalized", "accessibility_status"}
            missing_columns = required_columns.difference(reader.fieldnames or [])
            if missing_columns:
                raise OdsayBusRouteError("low-floor bus route master has invalid columns", reason="invalid_route_master")

            for row in reader:
                normalized = normalize_route_number(str(row.get("route_number_normalized") or ""))
                route_number = str(row.get("route_number") or "").strip()
                status = str(row.get("accessibility_status") or "").strip().lower()
                if not normalized or not route_number or status not in {"available", "unavailable", "unknown"}:
                    raise OdsayBusRouteError("low-floor bus route master has invalid row", reason="invalid_route_master")
                if normalized in lookup:
                    raise OdsayBusRouteError("low-floor bus route number must be unique", reason="duplicate_route_number")
                lookup[normalized] = (route_number, status)
        return lookup

    @staticmethod
    def _load_mapping_lookup(
        mapping_path: Path,
        route_lookup: dict[str, tuple[str, str]],
    ) -> dict[int, LowFloorBusRouteEntry]:
        if not mapping_path.exists():
            raise OdsayBusRouteError("ODsay bus route mapping is missing", reason="missing_route_mapping")
        lookup: dict[int, LowFloorBusRouteEntry] = {}
        with mapping_path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            required_columns = {"odsay_bus_id", "odsay_bus_no", "odsay_bus_type", "route_number_normalized"}
            if required_columns.difference(reader.fieldnames or []):
                raise OdsayBusRouteError("ODsay bus route mapping has invalid columns", reason="invalid_route_mapping")
            for row in reader:
                bus_id = _coerce_non_negative_int(row.get("odsay_bus_id"), "odsay_bus_id")
                bus_type = _coerce_non_negative_int(row.get("odsay_bus_type"), "odsay_bus_type")
                bus_no = normalize_route_number(str(row.get("odsay_bus_no") or ""))
                normalized = normalize_route_number(str(row.get("route_number_normalized") or ""))
                route = route_lookup.get(normalized)
                if not bus_no or bus_no != normalized or route is None:
                    raise OdsayBusRouteError("ODsay bus route mapping has invalid row", reason="invalid_route_mapping")
                if bus_id in lookup:
                    raise OdsayBusRouteError("ODsay busID must be unique", reason="duplicate_odsay_bus_id")
                route_number, status = route
                lookup[bus_id] = LowFloorBusRouteEntry(
                    odsay_bus_id=bus_id,
                    odsay_bus_type=bus_type,
                    route_number=route_number,
                    route_number_normalized=normalized,
                    accessibility_status=status,
                )
        return lookup


class OdsayLowFloorBusRouteClient:
    """ODsay 버스 전용 경로를 조회하고 저상버스 route master로 필터링한다."""

    def __init__(
        self,
        api_key: str,
        route_provider: LowFloorBusRouteProvider,
        http_client: httpx.Client | None = None,
        route_url: str = ODSAY_BUS_ROUTE_URL,
    ) -> None:
        if not api_key:
            raise ValueError("ODsay API key is required")
        self.api_key = api_key
        self.route_provider = route_provider
        self.http_client = http_client
        self.route_url = route_url

    def get_low_floor_bus_route(self, origin: Location, destination: Location) -> LowFloorBusRouteMetrics:
        params = {
            "SX": origin.longitude,
            "SY": origin.latitude,
            "EX": destination.longitude,
            "EY": destination.latitude,
            "SearchType": 0,
            "SearchPathType": BUS_PATH_TYPE,
            "apiKey": self.api_key,
        }

        try:
            if self.http_client is None:
                with httpx.Client(timeout=10) as client:
                    response = client.get(self.route_url, params=params)
            else:
                response = self.http_client.get(self.route_url, params=params)
        except httpx.HTTPError as exc:
            raise OdsayBusRouteError("ODsay bus route API request failed", reason=exc.__class__.__name__) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OdsayBusRouteError(
                "ODsay bus route API returned an error status",
                reason=f"status_code={exc.response.status_code}",
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise OdsayBusRouteError("ODsay bus route API returned invalid JSON", reason="invalid_json") from exc

        if isinstance(payload, dict) and "error" in payload:
            raise OdsayBusRouteError("ODsay bus route API returned an application error", reason="odsay_api_error")
        return parse_odsay_low_floor_bus_route(payload, self.route_provider)


def parse_odsay_low_floor_bus_route(
    payload: dict[str, Any],
    route_provider: LowFloorBusRouteProvider,
) -> LowFloorBusRouteMetrics:
    """첫 번째 저상버스 이용 가능 경로와 모든 도보 subPath 합계를 반환한다."""

    result = _require_mapping(payload.get("result"), reason="missing_result")
    paths = _require_list(result.get("path"), reason="missing_path")
    for path_value in paths:
        path = _require_mapping(path_value, reason="invalid_path")
        if path.get("pathType") != BUS_PATH_TYPE:
            continue
        sub_paths = path.get("subPath")
        if not isinstance(sub_paths, list) or not _is_bus_only_path(sub_paths):
            continue
        selected_lanes = _select_accessible_lanes(sub_paths, route_provider)
        if selected_lanes is None:
            continue
        return _build_metrics(path, sub_paths, selected_lanes)
    raise LowFloorBusRouteUnavailableError("ODsay response does not include an accessible low-floor bus route")


def normalize_route_number(value: str) -> str:
    """확정된 route master 규칙대로 공백 제거·대문자화하고 선행 0은 유지한다."""

    return "".join(value.strip().split()).upper()


def _is_bus_only_path(sub_paths: list[Any]) -> bool:
    has_bus = False
    for section in sub_paths:
        if not isinstance(section, dict):
            return False
        traffic_type = section.get("trafficType")
        if traffic_type == BUS_TRAFFIC_TYPE:
            has_bus = True
        elif traffic_type != WALKING_TRAFFIC_TYPE:
            return False
    return has_bus


def _select_accessible_lanes(
    sub_paths: list[Any],
    route_provider: LowFloorBusRouteProvider,
) -> tuple[SelectedBusLane, ...] | None:
    selected: list[SelectedBusLane] = []
    for section in sub_paths:
        if not isinstance(section, dict) or section.get("trafficType") != BUS_TRAFFIC_TYPE:
            continue
        lanes = section.get("lane")
        if not isinstance(lanes, list):
            return None
        matched_lane: SelectedBusLane | None = None
        for lane in lanes:
            if not isinstance(lane, dict) or not isinstance(lane.get("busNo"), str):
                continue
            bus_id = _strict_non_negative_int(lane.get("busID"))
            bus_type = _strict_non_negative_int(lane.get("type"))
            if bus_id is None or bus_type is None:
                continue
            entry = route_provider.get_route(bus_id, lane["busNo"], bus_type)
            if entry is not None and entry.accessibility_status == "available":
                matched_lane = SelectedBusLane(
                    route_number=entry.route_number,
                    route_number_normalized=entry.route_number_normalized,
                    start_stop_name=_optional_text(section.get("startName")),
                    end_stop_name=_optional_text(section.get("endName")),
                )
                break
        if matched_lane is None:
            return None
        selected.append(matched_lane)
    return tuple(selected) if selected else None


def _build_metrics(
    path: dict[str, Any],
    sub_paths: list[Any],
    selected_lanes: tuple[SelectedBusLane, ...],
) -> LowFloorBusRouteMetrics:
    info = _require_mapping(path.get("info"), reason="missing_info")
    total_time_seconds = _coerce_non_negative_int(info.get("totalTime"), "totalTime") * 60
    total_distance_meters = _coerce_optional_non_negative_distance(info.get("totalDistance"), 0, "totalDistance")
    fare_won = _coerce_optional_non_negative_int(info.get("payment"), 0, "payment")
    walking_distance_meters = _sum_section_values(sub_paths, WALKING_TRAFFIC_TYPE, "distance")
    walking_time_seconds = _sum_section_values(sub_paths, WALKING_TRAFFIC_TYPE, "sectionTime") * 60
    if total_distance_meters == 0:
        total_distance_meters = _sum_all_distances(sub_paths)
    if walking_time_seconds > total_time_seconds:
        raise OdsayBusRouteError("walking time exceeds total time", reason="invalid_walking_time")
    if walking_distance_meters > total_distance_meters:
        raise OdsayBusRouteError("walking distance exceeds total distance", reason="invalid_walking_distance")

    route_label = " → ".join(lane.route_number for lane in selected_lanes)
    return LowFloorBusRouteMetrics(
        total_time_seconds=total_time_seconds,
        total_distance_meters=total_distance_meters,
        walking_distance_meters=walking_distance_meters,
        walking_time_seconds=walking_time_seconds,
        fare_won=fare_won,
        selected_lanes=selected_lanes,
        summary=f"{route_label} 저상버스 경로",
    )


def _sum_section_values(sub_paths: list[Any], traffic_type: int, field_name: str) -> int:
    return sum(
        (
            _coerce_required_non_negative_distance(section.get(field_name), field_name)
            if field_name == "distance"
            else _coerce_required_non_negative_int(section.get(field_name), field_name)
        )
        for section in sub_paths
        if isinstance(section, dict) and section.get("trafficType") == traffic_type
    )


def _sum_all_distances(sub_paths: list[Any]) -> int:
    return sum(
        _coerce_optional_non_negative_distance(section.get("distance"), 0, "distance")
        for section in sub_paths
        if isinstance(section, dict)
    )


def _require_mapping(value: Any, reason: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OdsayBusRouteError("ODsay bus route response has invalid structure", reason=reason)
    return value


def _require_list(value: Any, reason: str) -> list[Any]:
    if not isinstance(value, list):
        raise OdsayBusRouteError("ODsay bus route response has invalid structure", reason=reason)
    return value


def _coerce_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise OdsayBusRouteError(f"{field_name} must be a non-negative integer", reason=f"invalid_{field_name}")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise OdsayBusRouteError(
            f"{field_name} must be a non-negative integer", reason=f"invalid_{field_name}"
        ) from exc
    if number < 0:
        raise OdsayBusRouteError(f"{field_name} must be non-negative", reason=f"negative_{field_name}")
    return number


def _coerce_optional_non_negative_int(value: Any, default: int, field_name: str) -> int:
    if value is None:
        return default
    return _coerce_non_negative_int(value, field_name)


def _coerce_optional_non_negative_distance(value: Any, default: int, field_name: str) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise OdsayBusRouteError(f"{field_name} must be a non-negative number", reason=f"invalid_{field_name}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise OdsayBusRouteError(
            f"{field_name} must be a non-negative number", reason=f"invalid_{field_name}"
        ) from exc
    if number < 0 or number != number or number == float("inf"):
        raise OdsayBusRouteError(f"{field_name} must be finite and non-negative", reason=f"invalid_{field_name}")
    return round(number)


def _coerce_required_non_negative_distance(value: Any, field_name: str) -> int:
    if value is None:
        raise OdsayBusRouteError(f"{field_name} is required", reason=f"missing_{field_name}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OdsayBusRouteError(f"{field_name} must be a number", reason=f"invalid_{field_name}")
    return _coerce_optional_non_negative_distance(value, 0, field_name)


def _coerce_required_non_negative_int(value: Any, field_name: str) -> int:
    if value is None:
        raise OdsayBusRouteError(f"{field_name} is required", reason=f"missing_{field_name}")
    if isinstance(value, bool) or not isinstance(value, int):
        raise OdsayBusRouteError(f"{field_name} must be an integer", reason=f"invalid_{field_name}")
    return _coerce_non_negative_int(value, field_name)


def _strict_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
