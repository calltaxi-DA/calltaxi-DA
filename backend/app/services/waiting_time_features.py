"""장애인 콜택시 대기시간 Prediction용 Backend feature mapping.

이 모듈은 Backend가 확보한 입력값을 AI Adapter의 `WaitingTimePredictionInput`으로
변환한다. 모델 artifact를 읽거나 예측을 수행하지 않으며, `data/` 또는 `notebooks*/`
경로를 참조하지 않는다.
"""

import math
from dataclasses import dataclass
from datetime import datetime

from ai.waiting_time.estimator import SUPPORTED_MODEL_GROUPS, WaitingTimePredictionInput

CONSERVATIVE_MODEL_GROUP_WARNING = (
    "실제 배차 차량군을 요청 시점에 확정할 수 없어 임차택시/특장차 바로콜 예측 중 더 긴 값을 사용했습니다."
)
SPECIAL_VEHICLE_MODEL_GROUP = "특장차_바로콜"

SEOUL_DISTRICTS = frozenset(
    {
        "강남구",
        "강동구",
        "강북구",
        "강서구",
        "관악구",
        "광진구",
        "구로구",
        "금천구",
        "노원구",
        "도봉구",
        "동대문구",
        "동작구",
        "마포구",
        "서대문구",
        "서초구",
        "성동구",
        "성북구",
        "송파구",
        "양천구",
        "영등포구",
        "용산구",
        "은평구",
        "종로구",
        "중구",
        "중랑구",
    }
)


class WaitingTimeFeatureMappingError(ValueError):
    """Backend 입력값을 Prediction feature로 변환할 수 없을 때 발생한다."""


@dataclass(frozen=True)
class SpecialVehiclePredictionFeatureSource:
    """특장차 대기시간 Prediction feature 생성을 위한 Backend 입력값."""

    requested_at: datetime
    purpose: str
    ride_distance_meters: float
    origin_gu: str | None
    origin_dong: str | None
    destination_gu: str | None
    destination_dong: str | None
    vehicle_operation_count_prev_day: float
    temperature_c: float
    precipitation_mm: float
    wind_speed_ms: float
    snow_depth_cm: float
    new_snow_3h_cm: float


def build_special_vehicle_waiting_time_input(
    source: SpecialVehiclePredictionFeatureSource,
) -> WaitingTimePredictionInput:
    """특장차 Backend 입력값을 AI Adapter 입력 계약으로 변환한다."""

    return build_waiting_time_inputs(source, model_groups=(SPECIAL_VEHICLE_MODEL_GROUP,))[0]


def build_waiting_time_inputs(
    source: SpecialVehiclePredictionFeatureSource,
    model_groups: tuple[str, ...] = SUPPORTED_MODEL_GROUPS,
) -> tuple[WaitingTimePredictionInput, ...]:
    """Backend 입력값을 지정된 model_group별 AI Adapter 입력 계약으로 변환한다."""

    origin_gu = _required_text(source.origin_gu, "origin_gu")
    destination_gu = _required_text(source.destination_gu, "destination_gu")

    try:
        return tuple(
            WaitingTimePredictionInput(
                requested_at=source.requested_at,
                purpose=source.purpose,
                ride_distance_meters=source.ride_distance_meters,
                origin_gu=origin_gu,
                origin_dong=_required_text(source.origin_dong, "origin_dong"),
                destination_gu=destination_gu,
                destination_dong=_required_text(source.destination_dong, "destination_dong"),
                movement_type=derive_movement_type(origin_gu, destination_gu),
                model_group=model_group,
                vehicle_operation_count_prev_day=source.vehicle_operation_count_prev_day,
                temperature_c=source.temperature_c,
                precipitation_mm=source.precipitation_mm,
                wind_speed_ms=source.wind_speed_ms,
                snow_depth_cm=source.snow_depth_cm,
                is_bad_weather=derive_is_bad_weather(
                    temperature_c=source.temperature_c,
                    precipitation_mm=source.precipitation_mm,
                    wind_speed_ms=source.wind_speed_ms,
                    snow_depth_cm=source.snow_depth_cm,
                    new_snow_3h_cm=source.new_snow_3h_cm,
                ),
            )
            for model_group in model_groups
        )
    except ValueError as exc:
        raise WaitingTimeFeatureMappingError(str(exc)) from exc


def derive_movement_type(origin_gu: str | None, destination_gu: str | None) -> str:
    """출발/목적 구 기준으로 학습 당시 `세부이동유형` label을 파생한다."""

    origin_gu = _required_text(origin_gu, "origin_gu")
    destination_gu = _required_text(destination_gu, "destination_gu")
    origin_in_seoul = origin_gu in SEOUL_DISTRICTS
    destination_in_seoul = destination_gu in SEOUL_DISTRICTS

    if origin_in_seoul and destination_in_seoul:
        if origin_gu == destination_gu:
            return "구 내 이동"
        return "구 간 이동"
    if origin_in_seoul and not destination_in_seoul:
        return "서울→서울 외"
    if not origin_in_seoul and destination_in_seoul:
        return "서울 외→서울"
    raise WaitingTimeFeatureMappingError("서울 외↔서울 외 이동은 대기시간 Prediction 대상이 아닙니다")


def derive_is_bad_weather(
    *,
    temperature_c: float,
    precipitation_mm: float,
    wind_speed_ms: float,
    snow_depth_cm: float,
    new_snow_3h_cm: float,
) -> bool:
    """학습 feature mapping 문서의 악천후 rule을 그대로 적용한다."""

    numeric_values = {
        "temperature_c": temperature_c,
        "precipitation_mm": precipitation_mm,
        "wind_speed_ms": wind_speed_ms,
        "snow_depth_cm": snow_depth_cm,
        "new_snow_3h_cm": new_snow_3h_cm,
    }
    for field_name, value in numeric_values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise WaitingTimeFeatureMappingError(f"{field_name}은 유한한 숫자여야 합니다")
    if precipitation_mm < 0:
        raise WaitingTimeFeatureMappingError("precipitation_mm은 0 이상이어야 합니다")
    if wind_speed_ms < 0:
        raise WaitingTimeFeatureMappingError("wind_speed_ms는 0 이상이어야 합니다")
    if snow_depth_cm < 0:
        raise WaitingTimeFeatureMappingError("snow_depth_cm은 0 이상이어야 합니다")
    if new_snow_3h_cm < 0:
        raise WaitingTimeFeatureMappingError("new_snow_3h_cm은 0 이상이어야 합니다")

    is_rain = precipitation_mm > 0
    is_snow = (snow_depth_cm > 0) or (new_snow_3h_cm > 0)
    is_cold_wave_like = temperature_c <= -5
    is_strong_wind = wind_speed_ms >= 5
    return is_rain or is_snow or is_cold_wave_like or is_strong_wind


def _required_text(value: str | None, field_name: str) -> str:
    if not isinstance(value, str):
        raise WaitingTimeFeatureMappingError(f"{field_name}은 문자열이어야 합니다")
    normalized = value.strip()
    if not normalized:
        raise WaitingTimeFeatureMappingError(f"{field_name}은 비어 있을 수 없습니다")
    return normalized
