from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from ai.waiting_time.estimator import (
    MODEL_FEATURE_COLUMNS,
    WaitingTimePredictionInput,
    estimate_waiting_minutes,
    estimate_waiting_minutes_for_input,
)


def test_estimate_waiting_minutes_raises_when_model_not_connected() -> None:
    """모델 연결 전까지는 가짜 값 대신 NotImplementedError로 명확히 실패해야 한다."""
    with pytest.raises(NotImplementedError):
        estimate_waiting_minutes(9)


def test_estimate_waiting_minutes_rejects_invalid_hour() -> None:
    with pytest.raises(ValueError):
        estimate_waiting_minutes(24)


def _prediction_input(**overrides: object) -> WaitingTimePredictionInput:
    values: dict[str, object] = {
        "requested_at": datetime(2026, 9, 13, 14, 30, tzinfo=ZoneInfo("Asia/Seoul")),
        "purpose": "치료",
        "ride_distance_meters": 12345.0,
        "origin_gu": "중구",
        "origin_dong": "명동",
        "destination_gu": "강남구",
        "destination_dong": "역삼동",
        "movement_type": "구 간 이동",
        "model_group": "특장차_바로콜",
        "vehicle_operation_count_prev_day": 412.0,
        "temperature_c": 23.5,
        "precipitation_mm": 0.0,
        "wind_speed_ms": 2.1,
        "snow_depth_cm": 0.0,
        "is_bad_weather": False,
    }
    values.update(overrides)
    return WaitingTimePredictionInput(**values)  # type: ignore[arg-type]


def test_prediction_input_maps_to_training_feature_contract() -> None:
    prediction_input = _prediction_input(is_bad_weather=True)

    features = prediction_input.to_model_features()

    assert tuple(features.keys()) == MODEL_FEATURE_COLUMNS
    assert features == {
        "hour": 14,
        "이용목적": "치료",
        "승차거리": 12345.0,
        "출발동": "명동",
        "목적동": "역삼동",
        "출발구": "중구",
        "목적구": "강남구",
        "month": 9,
        "세부이동유형": "구 간 이동",
        "dayofweek": 6,
        "model_group": "특장차_바로콜",
        "vehicle_operation_count_prev_day": 412.0,
        "temperature_c": 23.5,
        "precipitation_mm": 0.0,
        "wind_speed_ms": 2.1,
        "snow_depth_cm": 0.0,
        "is_bad_weather": 1,
    }


def test_prediction_input_rejects_out_of_serving_hours() -> None:
    with pytest.raises(ValueError, match="02:00~06:59"):
        _prediction_input(requested_at=datetime(2026, 9, 13, 3, 0, tzinfo=ZoneInfo("Asia/Seoul")))


def test_prediction_input_rejects_unsupported_category() -> None:
    with pytest.raises(ValueError, match="지원하지 않는 이용목적"):
        _prediction_input(purpose="예약치료")


def test_prediction_input_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _prediction_input(requested_at=datetime(2026, 9, 13, 14, 30))


def test_prediction_input_based_estimator_raises_until_model_artifact_is_connected() -> None:
    with pytest.raises(NotImplementedError):
        estimate_waiting_minutes_for_input(_prediction_input())
