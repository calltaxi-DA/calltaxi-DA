"""장애인 콜택시 자동차 경로와 요금 계산.

TMAP 자동차 경로안내 API의 간소화 응답(`totalValue=2`)에서
차량 이동거리(`totalDistance`, m)와 차량 이동시간(`totalTime`, sec)을 사용한다.

서울 장애인콜택시 예상요금은 현재 공식 안내 기준을 거리 기반으로 계산한다.
- 5km까지: 1,500원
- 5km 초과 10km까지: km당 280원
- 10km 초과: km당 70원
- 100원 미만 절사
"""

from typing import Any

import httpx

from app.api.contracts import Location

TMAP_ROUTE_URL = "https://apis.openapi.sk.com/tmap/routes"

CALLTAXI_BASE_DISTANCE_METERS = 5_000
CALLTAXI_SECOND_DISTANCE_METERS = 10_000
CALLTAXI_BASE_FARE_WON = 1_500
CALLTAXI_SECOND_SECTION_RATE_WON_PER_KM = 280
CALLTAXI_AFTER_SECOND_RATE_WON_PER_KM = 70


class TmapRouteError(RuntimeError):
    """TMAP 자동차 경로를 계산할 수 없을 때 발생한다."""


class TmapRouteClient:
    """TMAP 자동차 경로안내 API 클라이언트."""

    def __init__(
        self,
        app_key: str,
        http_client: httpx.Client | None = None,
        route_url: str = TMAP_ROUTE_URL,
    ) -> None:
        if not app_key:
            raise ValueError("TMAP app key is required")
        self.app_key = app_key
        self.http_client = http_client
        self.route_url = route_url

    def get_vehicle_route(self, origin: Location, destination: Location) -> tuple[int, int]:
        """출발지·목적지 좌표로 차량 이동거리(m)와 차량 이동시간(sec)을 반환한다."""

        payload = {
            "startX": origin.longitude,
            "startY": origin.latitude,
            "endX": destination.longitude,
            "endY": destination.latitude,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "searchOption": 0,
            "totalValue": 2,
        }
        params = {"version": "1"}
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "appKey": self.app_key,
        }

        try:
            if self.http_client is None:
                with httpx.Client(timeout=10) as client:
                    response = client.post(self.route_url, params=params, headers=headers, json=payload)
            else:
                response = self.http_client.post(self.route_url, params=params, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise TmapRouteError("TMAP route API request failed") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TmapRouteError("TMAP route API returned an error status") from exc

        return parse_tmap_route_metrics(response.json())


def parse_tmap_route_metrics(payload: dict[str, Any]) -> tuple[int, int]:
    """TMAP 응답에서 totalDistance, totalTime을 꺼낸다."""

    try:
        properties = payload["features"][0]["properties"]
        distance = properties["totalDistance"]
        time = properties["totalTime"]
    except (KeyError, IndexError, TypeError) as exc:
        raise TmapRouteError("TMAP route API response does not include route metrics") from exc

    if not isinstance(distance, int) or not isinstance(time, int):
        raise TmapRouteError("TMAP route metrics must be integers")
    if distance < 0 or time < 0:
        raise TmapRouteError("TMAP route metrics must not be negative")
    return distance, time


def calculate_seoul_calltaxi_fare(distance_meters: int) -> int:
    """서울 장애인콜택시 공식 요금 기준으로 예상요금(원)을 계산한다."""

    if distance_meters < 0:
        raise ValueError("distance_meters must not be negative")

    if distance_meters <= CALLTAXI_BASE_DISTANCE_METERS:
        return CALLTAXI_BASE_FARE_WON

    if distance_meters <= CALLTAXI_SECOND_DISTANCE_METERS:
        extra_km = (distance_meters - CALLTAXI_BASE_DISTANCE_METERS) / 1_000
        fare = CALLTAXI_BASE_FARE_WON + extra_km * CALLTAXI_SECOND_SECTION_RATE_WON_PER_KM
        return _floor_to_100_won(fare)

    second_section_fare = (
        CALLTAXI_BASE_FARE_WON
        + ((CALLTAXI_SECOND_DISTANCE_METERS - CALLTAXI_BASE_DISTANCE_METERS) / 1_000)
        * CALLTAXI_SECOND_SECTION_RATE_WON_PER_KM
    )
    extra_km = (distance_meters - CALLTAXI_SECOND_DISTANCE_METERS) / 1_000
    fare = second_section_fare + extra_km * CALLTAXI_AFTER_SECOND_RATE_WON_PER_KM
    return _floor_to_100_won(fare)


def _floor_to_100_won(fare: float) -> int:
    return int(fare // 100 * 100)
