"""이동수단 경로 비교에 공통으로 쓰는 API 계약.

단위:
- 시간: 초
- 거리: 미터
- 비용: 원
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class TransportType(StrEnum):
    """서비스가 비교하는 이동수단 종류."""

    CALLTAXI = "calltaxi"
    SUBWAY = "subway"
    LOW_FLOOR_BUS = "low_floor_bus"


class Location(BaseModel):
    """출발지·목적지 등 위치 표현."""

    name: str | None = Field(default=None, description="사용자에게 보여줄 장소명")
    latitude: float = Field(description="WGS84 위도")
    longitude: float = Field(description="WGS84 경도")
    address: str | None = Field(default=None, description="주소 또는 행정구역명")


class RouteResult(BaseModel):
    """이동수단별 경로 결과의 공통 응답 단위."""

    transport_type: TransportType
    total_time_seconds: int = Field(ge=0, description="총 소요 시간(초)")
    total_distance_meters: int = Field(ge=0, description="총 이동 거리(미터)")
    total_cost_won: int = Field(ge=0, description="예상 비용(원)")
    walking_distance_meters: int = Field(ge=0, description="도보 거리(미터)")
    walking_time_seconds: int = Field(ge=0, description="도보 시간(초)")
    summary: str | None = Field(default=None, description="경로 요약 문구")
    warnings: list[str] = Field(default_factory=list, description="주의 조건")


class RouteComparisonResponse(BaseModel):
    """출발지·목적지 기준 3개 이동수단 비교 응답."""

    origin: Location
    destination: Location
    routes: list[RouteResult]
