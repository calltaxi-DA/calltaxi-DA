"""ODsay 지하철 경로 응답 파싱과 접근성 검사.

이번 Phase는 ODsay 지하철 경로 API 응답에서 총 이동시간과 도보 구간을
계산하고, 검토 완료된 접근성 lookup이 주입될 수 있는 경계를 만든다.
서비스 코드는 `data/processed`를 직접 읽지 않는다.
"""

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.api.contracts import Location

ODSAY_SUBWAY_ROUTE_URL = "https://api.odsay.com/v1/api/searchPubTransPathT"
WALKING_TRAFFIC_TYPE = 3
SUBWAY_TRAFFIC_TYPE = 1


class OdsayRouteError(RuntimeError):
    """ODsay 지하철 경로를 계산할 수 없을 때 발생한다."""

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class SubwayStationKey:
    """접근성 lookup에 사용하는 역 key.

    `line_name`은 ODsay 응답의 노선명을 backend에서 정규화한 값이다.
    실제 stationID 기반 전체 매핑은 후속 export Phase에서 확정한다.
    """

    line_name: str
    station_name: str


@dataclass(frozen=True)
class SubwayRouteMetrics:
    total_time_seconds: int
    total_distance_meters: int
    walking_distance_meters: int
    walking_time_seconds: int
    fare_won: int
    station_keys: tuple[SubwayStationKey, ...]
    summary: str


@dataclass(frozen=True)
class StationAccessibility:
    has_operating_elevator: bool
    elevator_count: int = 0
    elevator_location: str | None = None
    elevator_floor_connection: str | None = None


class SubwayAccessibilityProvider(Protocol):
    """지하철 접근성 lookup provider.

    후속 Phase에서 `analysis/`에 export된 station accessibility master를
    읽는 구현으로 대체한다. 이번 Phase의 기본 구현은 아무 lookup도
    제공하지 않는다.
    """

    def get_station_accessibility(self, station_key: SubwayStationKey) -> StationAccessibility | None:
        ...


class EmptySubwayAccessibilityProvider:
    """아직 접근성 lookup export가 없을 때 사용하는 기본 provider."""

    def get_station_accessibility(self, station_key: SubwayStationKey) -> StationAccessibility | None:
        return None


class OdsaySubwayRouteClient:
    """ODsay 대중교통 경로 API 클라이언트."""

    def __init__(
        self,
        api_key: str,
        http_client: httpx.Client | None = None,
        route_url: str = ODSAY_SUBWAY_ROUTE_URL,
    ) -> None:
        if not api_key:
            raise ValueError("ODsay API key is required")
        self.api_key = api_key
        self.http_client = http_client
        self.route_url = route_url

    def get_subway_route(self, origin: Location, destination: Location) -> SubwayRouteMetrics:
        """출발지·목적지 좌표로 지하철 경로 지표를 반환한다."""

        params = {
            "SX": origin.longitude,
            "SY": origin.latitude,
            "EX": destination.longitude,
            "EY": destination.latitude,
            "apiKey": self.api_key,
        }

        try:
            if self.http_client is None:
                with httpx.Client(timeout=10) as client:
                    response = client.get(self.route_url, params=params)
            else:
                response = self.http_client.get(self.route_url, params=params)
        except httpx.HTTPError as exc:
            raise OdsayRouteError("ODsay subway route API request failed", reason=exc.__class__.__name__) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OdsayRouteError(
                "ODsay subway route API returned an error status",
                reason=f"status_code={exc.response.status_code}",
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise OdsayRouteError("ODsay subway route API returned invalid JSON", reason="invalid_json") from exc

        return parse_odsay_subway_route(payload)


def parse_odsay_subway_route(payload: dict[str, Any]) -> SubwayRouteMetrics:
    """ODsay 응답에서 첫 번째 지하철 경로의 시간·거리·도보 지표를 꺼낸다."""

    path = _select_first_subway_path(payload)
    info = _require_mapping(path.get("info"), reason="missing_info")
    sub_paths = _require_list(path.get("subPath"), reason="missing_sub_path")

    total_time_minutes = _coerce_non_negative_int(info.get("totalTime"), field_name="totalTime")
    fare_won = _coerce_optional_non_negative_int(info.get("payment"), default=0, field_name="payment")
    total_distance_meters = _coerce_optional_non_negative_int(info.get("totalDistance"), default=0, field_name="totalDistance")

    walking_distance_meters = _sum_walking_distance_meters(sub_paths)
    walking_time_seconds = _sum_walking_time_seconds(sub_paths)
    station_keys = tuple(_extract_station_keys(sub_paths))

    if total_distance_meters == 0:
        # 일부 ODsay 응답/Mock은 totalDistance 없이 구간별 거리만 제공한다.
        total_distance_meters = walking_distance_meters + _sum_non_walking_distance_meters(sub_paths)

    if walking_time_seconds > total_time_minutes * 60:
        raise OdsayRouteError("walking time must not exceed total route time", reason="invalid_walking_time")
    if walking_distance_meters > total_distance_meters:
        raise OdsayRouteError("walking distance must not exceed total route distance", reason="invalid_walking_distance")

    return SubwayRouteMetrics(
        total_time_seconds=total_time_minutes * 60,
        total_distance_meters=total_distance_meters,
        walking_distance_meters=walking_distance_meters,
        walking_time_seconds=walking_time_seconds,
        fare_won=fare_won,
        station_keys=station_keys,
        summary=_build_summary(station_keys),
    )


def build_accessibility_warnings(
    station_keys: tuple[SubwayStationKey, ...],
    accessibility_provider: SubwayAccessibilityProvider,
) -> list[str]:
    """출발역·환승역·도착역의 접근성 주의 문구를 만든다."""

    if not station_keys:
        return ["지하철역 접근성 정보를 확인할 수 없습니다."]

    warnings: list[str] = []
    missing: list[str] = []
    no_elevator: list[str] = []

    for station_key in station_keys:
        accessibility = accessibility_provider.get_station_accessibility(station_key)
        label = f"{station_key.line_name} {station_key.station_name}"
        if accessibility is None:
            missing.append(label)
            continue
        if not accessibility.has_operating_elevator:
            no_elevator.append(label)

    if missing:
        warnings.append("접근성 lookup에 없는 역이 있어 상세 확인이 필요합니다: " + ", ".join(missing))
    if no_elevator:
        warnings.append("접근성 데이터 기준 운행 가능한 엘리베이터가 없는 역이 있습니다: " + ", ".join(no_elevator))
    if not warnings:
        warnings.append("접근성 데이터 기준 출발역·환승역·도착역 모두 운행 가능한 엘리베이터를 보유합니다.")
    warnings.append("실시간 엘리베이터 고장·점검 상태는 포함되지 않습니다.")
    return warnings


def _select_first_subway_path(payload: dict[str, Any]) -> dict[str, Any]:
    result = _require_mapping(payload.get("result"), reason="missing_result")
    paths = _require_list(result.get("path"), reason="missing_path")
    for path in paths:
        path_mapping = _require_mapping(path, reason="invalid_path")
        if _path_has_subway(path_mapping):
            return path_mapping
    raise OdsayRouteError("ODsay response does not include a subway route", reason="missing_subway_route")


def _path_has_subway(path: dict[str, Any]) -> bool:
    sub_paths = path.get("subPath")
    if not isinstance(sub_paths, list):
        return False
    return any(isinstance(section, dict) and section.get("trafficType") == SUBWAY_TRAFFIC_TYPE for section in sub_paths)


def _sum_walking_distance_meters(sub_paths: list[Any]) -> int:
    total = 0
    for section in sub_paths:
        if isinstance(section, dict) and section.get("trafficType") == WALKING_TRAFFIC_TYPE:
            total += _coerce_optional_non_negative_int(section.get("distance"), default=0, field_name="walk_distance")
    return total


def _sum_walking_time_seconds(sub_paths: list[Any]) -> int:
    total_minutes = 0
    for section in sub_paths:
        if isinstance(section, dict) and section.get("trafficType") == WALKING_TRAFFIC_TYPE:
            total_minutes += _coerce_optional_non_negative_int(section.get("sectionTime"), default=0, field_name="walk_sectionTime")
    return total_minutes * 60


def _sum_non_walking_distance_meters(sub_paths: list[Any]) -> int:
    total = 0
    for section in sub_paths:
        if isinstance(section, dict) and section.get("trafficType") != WALKING_TRAFFIC_TYPE:
            total += _coerce_optional_non_negative_int(section.get("distance"), default=0, field_name="section_distance")
    return total


def _extract_station_keys(sub_paths: list[Any]) -> list[SubwayStationKey]:
    station_keys: list[SubwayStationKey] = []
    for section in sub_paths:
        if not isinstance(section, dict) or section.get("trafficType") != SUBWAY_TRAFFIC_TYPE:
            continue
        line_name = _canonical_line_name(_extract_line_name(section))
        start_name = _normalize_station_name(section.get("startName"))
        end_name = _normalize_station_name(section.get("endName"))
        if start_name:
            station_keys.append(SubwayStationKey(line_name=line_name, station_name=start_name))
        if end_name:
            station_keys.append(SubwayStationKey(line_name=line_name, station_name=end_name))
    return _deduplicate_station_keys(station_keys)


def _extract_line_name(section: dict[str, Any]) -> str:
    lane = section.get("lane")
    if isinstance(lane, list) and lane and isinstance(lane[0], dict):
        line_name = lane[0].get("name")
        if isinstance(line_name, str) and line_name.strip():
            return line_name
    line_name = section.get("lineName")
    if isinstance(line_name, str) and line_name.strip():
        return line_name
    subway_code = section.get("subwayCode")
    if subway_code is not None:
        return f"{subway_code}호선"
    return "노선미상"


def _canonical_line_name(value: str) -> str:
    text = value.strip().replace(" ", "")
    aliases = {
        "1": "1호선",
        "2": "2호선",
        "3": "3호선",
        "4": "4호선",
        "5": "5호선",
        "6": "6호선",
        "7": "7호선",
        "8": "8호선",
        "9": "9호선",
        "수도권1호선": "1호선",
        "서울1호선": "1호선",
        "서울2호선": "2호선",
        "서울3호선": "3호선",
        "서울4호선": "4호선",
        "서울5호선": "5호선",
        "서울6호선": "6호선",
        "서울7호선": "7호선",
        "서울8호선": "8호선",
        "서울9호선": "9호선",
    }
    return aliases.get(text, text)


def _normalize_station_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().replace(" ", "")
    if text.endswith("역"):
        text = text[:-1]
    return text or None


def _deduplicate_station_keys(station_keys: list[SubwayStationKey]) -> list[SubwayStationKey]:
    seen: set[SubwayStationKey] = set()
    result: list[SubwayStationKey] = []
    for station_key in station_keys:
        if station_key in seen:
            continue
        seen.add(station_key)
        result.append(station_key)
    return result


def _build_summary(station_keys: tuple[SubwayStationKey, ...]) -> str:
    if len(station_keys) >= 2:
        return f"{station_keys[0].station_name}역 → {station_keys[-1].station_name}역 지하철 경로"
    return "지하철 경로"


def _require_mapping(value: Any, reason: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OdsayRouteError("ODsay route response has invalid structure", reason=reason)
    return value


def _require_list(value: Any, reason: str) -> list[Any]:
    if not isinstance(value, list):
        raise OdsayRouteError("ODsay route response has invalid structure", reason=reason)
    return value


def _coerce_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise OdsayRouteError(f"{field_name} must be a non-negative integer", reason=f"invalid_{field_name}")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise OdsayRouteError(f"{field_name} must be a non-negative integer", reason=f"invalid_{field_name}") from exc
    if number < 0:
        raise OdsayRouteError(f"{field_name} must be non-negative", reason=f"negative_{field_name}")
    return number


def _coerce_optional_non_negative_int(value: Any, default: int, field_name: str) -> int:
    if value is None:
        return default
    return _coerce_non_negative_int(value, field_name=field_name)
