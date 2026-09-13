"""AI Adapter: 장애인 콜택시 통합 대기시간 Prediction 모델 연동 계약.

이 모듈은 예측 모델 자체가 아니라, backend가 예측 모델을 호출하기 위해 쓰는
순수 Python 어댑터다. 서비스 코드는 `data/`나 `notebooks*/`를 직접 참조하지 않고,
검토 완료되어 `analysis/`에 export된 모델 산출물만 이 경계를 통해 사용한다.

Phase 0에서는 Backend가 넘겨야 하는 입력 계약과 모델 feature 변환만 정의한다.
아직 실제 모델 로딩/추론은 연결하지 않았으므로 호출 시 NotImplementedError를
발생시킨다 — 연결 전까지 가짜 값을 반환해 문제를 숨기지 않는다.

TODO: `analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib`과
메타데이터를 읽는 실제 모델 호출을 후속 AI 연결 Phase에서 구현한다.
"""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias

ModelFeatureValue: TypeAlias = str | int | float

TARGET_DEFINITION = "접수→승차 대기시간"
WAITING_TIME_UNIT = "minutes"
SUPPORTED_MODEL_GROUPS = ("임차택시_바로콜", "특장차_바로콜")
SUPPORTED_PURPOSES = ("기타", "귀가", "치료", "재활", "통학/출근", "종교")
SUPPORTED_MOVEMENT_TYPES = ("구 내 이동", "구 간 이동", "서울→서울 외", "서울 외→서울")
UNAVAILABLE_HOURS = tuple(range(2, 7))
TRAINING_TARGET_MAX_MINUTES = 130
MODEL_FEATURE_COLUMNS = (
    "hour",
    "이용목적",
    "승차거리",
    "출발동",
    "목적동",
    "출발구",
    "목적구",
    "month",
    "세부이동유형",
    "dayofweek",
    "model_group",
    "vehicle_operation_count_prev_day",
    "temperature_c",
    "precipitation_mm",
    "wind_speed_ms",
    "snow_depth_cm",
    "is_bad_weather",
)


@dataclass(frozen=True)
class WaitingTimeEstimate:
    expected_minutes: float
    hour_of_day: int
    model_name: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class WaitingTimePredictionInput:
    """통합 대기시간 모델에 넘길 1건 예측 입력.

    Backend는 경로 검색 시각, 주소 정규화, TMAP 차량거리, 전일 차량운행 대수,
    시간별 날씨 관측값을 먼저 확보한 뒤 이 타입으로 AI Adapter를 호출한다.
    `to_model_features()`는 학습 시 사용한 feature 이름과 단위에 맞춘 dict를 반환한다.
    """

    requested_at: datetime
    purpose: str
    ride_distance_meters: float
    origin_gu: str
    origin_dong: str
    destination_gu: str
    destination_dong: str
    movement_type: str
    model_group: str
    vehicle_operation_count_prev_day: float
    temperature_c: float
    precipitation_mm: float
    wind_speed_ms: float
    snow_depth_cm: float
    is_bad_weather: bool

    def __post_init__(self) -> None:
        if self.requested_at.tzinfo is None or self.requested_at.utcoffset() is None:
            raise ValueError("requested_at은 Asia/Seoul 기준 timezone-aware datetime이어야 합니다")
        if self.requested_at.hour in UNAVAILABLE_HOURS:
            raise ValueError("02:00~06:59 시간대는 일반구간 대기시간 모델 serving 대상이 아닙니다")
        if self.purpose not in SUPPORTED_PURPOSES:
            raise ValueError(f"지원하지 않는 이용목적입니다: {self.purpose}")
        if self.movement_type not in SUPPORTED_MOVEMENT_TYPES:
            raise ValueError(f"지원하지 않는 세부이동유형입니다: {self.movement_type}")
        if self.model_group not in SUPPORTED_MODEL_GROUPS:
            raise ValueError(f"지원하지 않는 model_group입니다: {self.model_group}")
        for field_name in ("origin_gu", "origin_dong", "destination_gu", "destination_dong"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name}은 비어 있을 수 없습니다")
        numeric_fields = (
            "ride_distance_meters",
            "vehicle_operation_count_prev_day",
            "temperature_c",
            "precipitation_mm",
            "wind_speed_ms",
            "snow_depth_cm",
        )
        for field_name in numeric_fields:
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field_name}은 유한한 숫자여야 합니다")
        if self.ride_distance_meters < 0:
            raise ValueError("ride_distance_meters는 0 이상이어야 합니다")
        if self.vehicle_operation_count_prev_day < 0:
            raise ValueError("vehicle_operation_count_prev_day는 0 이상이어야 합니다")

    def to_model_features(self) -> dict[str, ModelFeatureValue]:
        """학습 feature 이름·단위에 맞춘 모델 입력 dict를 반환한다."""

        features: dict[str, ModelFeatureValue] = {
            "hour": self.requested_at.hour,
            "이용목적": self.purpose,
            "승차거리": self.ride_distance_meters,
            "출발동": self.origin_dong,
            "목적동": self.destination_dong,
            "출발구": self.origin_gu,
            "목적구": self.destination_gu,
            "month": self.requested_at.month,
            "세부이동유형": self.movement_type,
            "dayofweek": self.requested_at.weekday(),
            "model_group": self.model_group,
            "vehicle_operation_count_prev_day": self.vehicle_operation_count_prev_day,
            "temperature_c": self.temperature_c,
            "precipitation_mm": self.precipitation_mm,
            "wind_speed_ms": self.wind_speed_ms,
            "snow_depth_cm": self.snow_depth_cm,
            "is_bad_weather": int(self.is_bad_weather),
        }
        return {column: features[column] for column in MODEL_FEATURE_COLUMNS}


def estimate_waiting_minutes(hour_of_day: int) -> WaitingTimeEstimate:
    """기존 Backend 호출부를 위한 임시 시간대 기반 어댑터.

    모델이 연결되기 전까지는 항상 NotImplementedError를 발생시킨다.
    호출하는 쪽(backend)은 이 예외를 잡아 "대기시간 예측 불가" 상태로 처리해야 한다.
    """
    if not 0 <= hour_of_day <= 23:
        raise ValueError("hour_of_day는 0~23 사이여야 합니다")

    raise NotImplementedError(
        "장애인 콜택시 통합 대기시간 Prediction 모델이 아직 연결되지 않았습니다."
    )


def estimate_waiting_minutes_for_input(
    prediction_input: WaitingTimePredictionInput,
) -> WaitingTimeEstimate:
    """통합 Prediction 입력 계약 기반 대기시간 예측 진입점.

    후속 연결 Phase에서 이 함수가 `analysis/`의 모델 artifact를 로딩하고,
    `prediction_input.to_model_features()` 결과를 모델에 전달한다.
    """

    _ = prediction_input.to_model_features()
    raise NotImplementedError(
        "장애인 콜택시 통합 대기시간 Prediction 모델 artifact 호출은 아직 연결되지 않았습니다."
    )
