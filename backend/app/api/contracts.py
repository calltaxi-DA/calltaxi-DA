"""이동수단 경로 비교에 공통으로 쓰는 API 계약.

단위:
- 시간: 초
- 거리: 미터
- 비용: 원
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TransportType(StrEnum):
    """서비스가 비교하는 이동수단 종류."""

    CALLTAXI = "calltaxi"
    SUBWAY = "subway"
    LOW_FLOOR_BUS = "low_floor_bus"


class RouteStatus(StrEnum):
    """이동수단별 경로 계산 가능 여부."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class MetricAvailability(StrEnum):
    """개별 비교 지표를 추천 정렬에 사용할 수 있는지 나타낸다."""

    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"


class AccessibilityStatus(StrEnum):
    """검토된 데이터 기준 접근성 확인 상태."""

    VERIFIED_AVAILABLE = "verified_available"
    VERIFIED_UNAVAILABLE = "verified_unavailable"
    NOT_VERIFIED = "not_verified"


class RecommendationPriority(StrEnum):
    """사용자가 지정할 수 있는 추천 정렬 기준."""

    TIME = "time"
    COST = "cost"
    WALK = "walk"


class RouteMetricAvailability(BaseModel):
    """RouteResult의 numeric field별 비교 가능 상태."""

    total_time_seconds: MetricAvailability = MetricAvailability.AVAILABLE
    total_distance_meters: MetricAvailability = MetricAvailability.AVAILABLE
    total_cost_won: MetricAvailability = MetricAvailability.AVAILABLE
    walking_distance_meters: MetricAvailability = MetricAvailability.AVAILABLE
    walking_time_seconds: MetricAvailability = MetricAvailability.AVAILABLE

    @classmethod
    def unavailable(cls) -> "RouteMetricAvailability":
        return cls(
            total_time_seconds=MetricAvailability.NOT_AVAILABLE,
            total_distance_meters=MetricAvailability.NOT_AVAILABLE,
            total_cost_won=MetricAvailability.NOT_AVAILABLE,
            walking_distance_meters=MetricAvailability.NOT_AVAILABLE,
            walking_time_seconds=MetricAvailability.NOT_AVAILABLE,
        )


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
    metric_availability: RouteMetricAvailability | None = Field(
        default=None,
        description="numeric field별 추천 비교 가능 상태. 생략 시 경로 상태에 맞춰 기본값을 적용한다.",
    )
    accessibility_status: AccessibilityStatus = Field(
        default=AccessibilityStatus.NOT_VERIFIED,
        description="검토된 데이터 기준 접근성 확인 상태",
    )
    unavailable_reason: str | None = Field(default=None, description="경로 계산 불가 사유")
    summary: str | None = Field(default=None, description="경로 요약 문구")
    warnings: list[str] = Field(default_factory=list, description="주의 조건")

    @model_validator(mode="after")
    def validate_route_status_and_units(self) -> "RouteResult":
        numeric_fields = {
            "total_time_seconds": self.total_time_seconds,
            "total_distance_meters": self.total_distance_meters,
            "total_cost_won": self.total_cost_won,
            "walking_distance_meters": self.walking_distance_meters,
            "walking_time_seconds": self.walking_time_seconds,
        }

        if self.status == RouteStatus.UNAVAILABLE:
            if any(value is not None for value in numeric_fields.values()):
                raise ValueError("unavailable route must not include numeric route metrics")
            if not self.unavailable_reason:
                raise ValueError("unavailable route requires unavailable_reason")
            if self.metric_availability is None:
                self.metric_availability = RouteMetricAvailability.unavailable()
            if any(
                availability != MetricAvailability.NOT_AVAILABLE
                for availability in self.metric_availability.model_dump().values()
            ):
                raise ValueError("unavailable route metrics must be marked not_available")
            return self

        if self.metric_availability is None:
            self.metric_availability = RouteMetricAvailability()
        for field_name, value in numeric_fields.items():
            availability = getattr(self.metric_availability, field_name)
            if availability == MetricAvailability.AVAILABLE and value is None:
                raise ValueError(f"available metric requires {field_name}")
            if availability == MetricAvailability.NOT_AVAILABLE and value is not None:
                raise ValueError(f"not_available metric must not include {field_name}")
        if self.unavailable_reason:
            raise ValueError("available route must not include unavailable_reason")
        if (
            self.walking_time_seconds is not None
            and self.total_time_seconds is not None
            and self.walking_time_seconds > self.total_time_seconds
        ):
            raise ValueError("walking_time_seconds must be less than or equal to total_time_seconds")
        if (
            self.walking_distance_meters is not None
            and self.total_distance_meters is not None
            and self.walking_distance_meters > self.total_distance_meters
        ):
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


class RecommendationRequest(BaseModel):
    """Backend가 경로를 계산할 출발지·목적지와 사용자 우선순위."""

    model_config = ConfigDict(extra="forbid")

    origin: Location
    destination: Location
    transport_types: list[TransportType] = Field(min_length=1, max_length=3)
    priorities: list[RecommendationPriority] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_unique_priorities(self) -> "RecommendationRequest":
        if len(self.transport_types) != len(set(self.transport_types)):
            raise ValueError("transport_types must not contain duplicates")
        if set(self.priorities) != set(RecommendationPriority):
            raise ValueError("priorities must contain each RecommendationPriority exactly once")
        return self


class RankedRoute(BaseModel):
    """추천 순위가 부여된 이동수단 경로."""

    rank: int = Field(ge=1, le=3)
    route: RouteResult


class ExcludedRoute(BaseModel):
    """추천 후보에서 제외된 경로와 사유."""

    transport_type: TransportType
    reason: str


class RecommendationResponse(BaseModel):
    """사용자 우선순위에 따른 최대 3개 추천 결과."""

    origin: Location
    destination: Location
    transport_types: list[TransportType] = Field(min_length=1, max_length=3)
    priorities: list[RecommendationPriority] = Field(min_length=3, max_length=3)
    recommendations: list[RankedRoute] = Field(max_length=3)
    excluded_routes: list[ExcludedRoute] = Field(default_factory=list)


class AnalysisSourcePeriod(BaseModel):
    start_date: str
    end_date: str
    basis: str
    timezone: str


class HospitalRegionCount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    count: int = Field(strict=True, ge=0)


class HospitalNeighborhoodCount(HospitalRegionCount):
    district: str


class HospitalDestinationValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    district_top5: list[HospitalRegionCount]
    neighborhood_top5: list[HospitalNeighborhoodCount]


class HospitalTripShare(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(strict=True, ge=0)
    percentage: float = Field(strict=True, ge=0, le=100)


class HospitalTripScopeValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    same_district: HospitalTripShare
    different_district: HospitalTripShare


class HospitalDistanceCoverageValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    same_district_within_5km_percentage: float = Field(strict=True, ge=0, le=100)
    different_district_within_5km_percentage: float = Field(strict=True, ge=0, le=100)
    overall_within_5km_percentage: float = Field(strict=True, ge=0, le=100)


class HospitalNetFlowRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    count: int = Field(strict=True)


class HospitalNetFlowValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    net_inflow_top5: list[HospitalNetFlowRegion]
    net_outflow_top5: list[HospitalNetFlowRegion]


class HospitalAnalysisBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    population_definition: str
    aggregation_unit: str
    limitations: list[str]


class HospitalDestinationAnalysis(HospitalAnalysisBase):
    analysis_id: Literal["medical_destination_top_regions"]
    values: HospitalDestinationValues


class HospitalTripScopeAnalysis(HospitalAnalysisBase):
    analysis_id: Literal["medical_trip_scope"]
    values: HospitalTripScopeValues


class HospitalDistanceCoverageAnalysis(HospitalAnalysisBase):
    analysis_id: Literal["medical_trip_distance_coverage"]
    values: HospitalDistanceCoverageValues


class HospitalNetFlowAnalysis(HospitalAnalysisBase):
    analysis_id: Literal["medical_net_flow_by_district"]
    values: HospitalNetFlowValues


HospitalAnalysisItem = Annotated[
    HospitalDestinationAnalysis
    | HospitalTripScopeAnalysis
    | HospitalDistanceCoverageAnalysis
    | HospitalNetFlowAnalysis,
    Field(discriminator="analysis_id"),
]


class HospitalAnalysisChart(BaseModel):
    chart_id: str
    title: str
    alt_text: str
    asset_url: str
    analysis_ids: list[str]


class HospitalAnalyticsResponse(BaseModel):
    schema_version: str
    source_period: AnalysisSourcePeriod
    analyses: list[HospitalAnalysisItem]
    charts: list[HospitalAnalysisChart]

    @model_validator(mode="after")
    def validate_analysis_and_chart_references(self) -> "HospitalAnalyticsResponse":
        analysis_ids = [analysis.analysis_id for analysis in self.analyses]
        expected_ids = {
            "medical_destination_top_regions",
            "medical_trip_scope",
            "medical_trip_distance_coverage",
            "medical_net_flow_by_district",
        }
        if len(analysis_ids) != len(expected_ids) or set(analysis_ids) != expected_ids:
            raise ValueError("hospital analytics must contain every analysis_id exactly once")

        chart_ids = [chart.chart_id for chart in self.charts]
        if len(chart_ids) != len(set(chart_ids)):
            raise ValueError("hospital chart_id values must be unique")
        if any(set(chart.analysis_ids).difference(expected_ids) for chart in self.charts):
            raise ValueError("hospital charts must reference known analysis_id values")
        return self


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
