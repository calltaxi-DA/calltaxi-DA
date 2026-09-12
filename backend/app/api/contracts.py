"""이동수단 경로 비교에 공통으로 쓰는 API 계약.

단위:
- 시간: 초
- 거리: 미터
- 비용: 원
"""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class TransportType(StrEnum):
    """서비스가 비교하는 이동수단 종류."""

    CALLTAXI = "calltaxi"
    SUBWAY = "subway"
    LOW_FLOOR_BUS = "low_floor_bus"


class RouteStatus(StrEnum):
    """이동수단별 경로 계산 가능 여부."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Location(BaseModel):
    """출발지·목적지 등 위치 표현."""

    name: str | None = Field(default=None, description="사용자에게 보여줄 장소명")
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False, description="WGS84 위도")
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False, description="WGS84 경도")
    address: str | None = Field(default=None, description="주소 또는 행정구역명")


class RouteResult(BaseModel):
    """이동수단별 경로 결과의 공통 응답 단위."""

    transport_type: TransportType
    status: RouteStatus = Field(description="경로 계산 가능 여부")
    total_time_seconds: int | None = Field(
        default=None,
        ge=0,
        description="총 소요 시간(초). 장애인 콜택시는 대기시간과 차량 이동시간을 포함한다.",
    )
    total_distance_meters: int | None = Field(
        default=None,
        ge=0,
        description="총 이동 거리(미터). 도보 구간을 포함한 전체 경로 거리다.",
    )
    total_cost_won: int | None = Field(default=None, ge=0, description="예상 비용(원)")
    walking_distance_meters: int | None = Field(default=None, ge=0, description="도보 거리(미터)")
    walking_time_seconds: int | None = Field(default=None, ge=0, description="도보 시간(초)")
    unavailable_reason: str | None = Field(default=None, description="경로 계산 불가 사유")
    summary: str | None = Field(default=None, description="경로 요약 문구")
    warnings: list[str] = Field(default_factory=list, description="주의 조건")

    @model_validator(mode="after")
    def validate_route_status_and_units(self) -> "RouteResult":
        numeric_fields = (
            self.total_time_seconds,
            self.total_distance_meters,
            self.total_cost_won,
            self.walking_distance_meters,
            self.walking_time_seconds,
        )

        if self.status == RouteStatus.UNAVAILABLE:
            if any(value is not None for value in numeric_fields):
                raise ValueError("unavailable route must not include numeric route metrics")
            if not self.unavailable_reason:
                raise ValueError("unavailable route requires unavailable_reason")
            return self

        if any(value is None for value in numeric_fields):
            raise ValueError("available route requires all numeric route metrics")
        if self.unavailable_reason:
            raise ValueError("available route must not include unavailable_reason")
        if self.walking_time_seconds > self.total_time_seconds:
            raise ValueError("walking_time_seconds must be less than or equal to total_time_seconds")
        if self.walking_distance_meters > self.total_distance_meters:
            raise ValueError("walking_distance_meters must be less than or equal to total_distance_meters")
        return self


class RouteComparisonResponse(BaseModel):
    """출발지·목적지 기준 3개 이동수단 비교 응답."""

    origin: Location
    destination: Location
    routes: list[RouteResult] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_exactly_one_route_per_transport_type(self) -> "RouteComparisonResponse":
        expected = set(TransportType)
        actual = [route.transport_type for route in self.routes]
        if set(actual) != expected or len(actual) != len(set(actual)):
            raise ValueError("routes must contain each TransportType exactly once")
        return self


class RouteRequest(BaseModel):
    """출발지·목적지 기반 단일 경로 계산 요청."""

    origin: Location
    destination: Location


class CalltaxiRouteResponse(BaseModel):
    """장애인 콜택시 차량 경로 계산 응답.

    이번 응답은 대기시간을 포함한 최종 RouteResult가 아니라
    TMAP 자동차 경로안내로 계산한 차량 이동 정보와 거리 기반 예상요금이다.
    """

    transport_type: TransportType = Field(default=TransportType.CALLTAXI)
    vehicle_distance_meters: int = Field(ge=0, description="TMAP 자동차 경로 기준 차량 이동거리(미터)")
    vehicle_time_seconds: int = Field(ge=0, description="TMAP 자동차 경로 기준 차량 이동시간(초)")
    estimated_fare_won: int = Field(ge=0, description="서울 장애인콜택시 거리요금 기준 예상요금(원)")
    warnings: list[str] = Field(default_factory=list, description="예상요금 산정 시 제외된 비용 등 안내")
