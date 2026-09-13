from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.waiting_time_features import (
    SPECIAL_VEHICLE_MODEL_GROUP,
    SpecialVehiclePredictionFeatureSource,
    WaitingTimeFeatureMappingError,
    build_special_vehicle_waiting_time_input,
    derive_is_bad_weather,
    derive_movement_type,
)


def _source(**overrides: object) -> SpecialVehiclePredictionFeatureSource:
    values: dict[str, object] = {
        "requested_at": datetime(2026, 9, 13, 0, 30, tzinfo=ZoneInfo("UTC")),
        "purpose": "치료",
        "ride_distance_meters": 12_500,
        "origin_gu": "중구",
        "origin_dong": "명동",
        "destination_gu": "강남구",
        "destination_dong": "역삼동",
        "vehicle_operation_count_prev_day": 412,
        "temperature_c": 23.5,
        "precipitation_mm": 0.0,
        "wind_speed_ms": 2.1,
        "snow_depth_cm": 0.0,
        "new_snow_3h_cm": 0.0,
    }
    values.update(overrides)
    return SpecialVehiclePredictionFeatureSource(**values)  # type: ignore[arg-type]


def test_build_special_vehicle_waiting_time_input_maps_backend_values_to_model_features() -> None:
    prediction_input = build_special_vehicle_waiting_time_input(_source(precipitation_mm=1.2))

    features = prediction_input.to_model_features()

    assert features["hour"] == 9
    assert features["month"] == 9
    assert features["dayofweek"] == 6
    assert features["이용목적"] == "치료"
    assert features["승차거리"] == 12_500
    assert features["출발구"] == "중구"
    assert features["출발동"] == "명동"
    assert features["목적구"] == "강남구"
    assert features["목적동"] == "역삼동"
    assert features["세부이동유형"] == "구 간 이동"
    assert features["model_group"] == SPECIAL_VEHICLE_MODEL_GROUP
    assert features["vehicle_operation_count_prev_day"] == 412
    assert features["temperature_c"] == 23.5
    assert features["precipitation_mm"] == 1.2
    assert features["wind_speed_ms"] == 2.1
    assert features["snow_depth_cm"] == 0.0
    assert features["is_bad_weather"] == 1


@pytest.mark.parametrize(
    ("origin_gu", "destination_gu", "expected"),
    [
        ("중구", "중구", "구 내 이동"),
        ("중구", "강남구", "구 간 이동"),
        ("중구", "성남시", "서울→서울 외"),
        ("성남시", "중구", "서울 외→서울"),
    ],
)
def test_derive_movement_type(origin_gu: str, destination_gu: str, expected: str) -> None:
    assert derive_movement_type(origin_gu, destination_gu) == expected


def test_derive_movement_type_rejects_outside_seoul_to_outside_seoul() -> None:
    with pytest.raises(WaitingTimeFeatureMappingError, match="서울 외↔서울 외"):
        derive_movement_type("성남시", "고양시")


@pytest.mark.parametrize(
    ("weather_overrides", "expected"),
    [
        ({}, False),
        ({"precipitation_mm": 0.1}, True),
        ({"snow_depth_cm": 0.1}, True),
        ({"new_snow_3h_cm": 0.1}, True),
        ({"temperature_c": -5.0}, True),
        ({"wind_speed_ms": 5.0}, True),
    ],
)
def test_derive_is_bad_weather(weather_overrides: dict[str, float], expected: bool) -> None:
    values = {
        "temperature_c": 10.0,
        "precipitation_mm": 0.0,
        "wind_speed_ms": 2.0,
        "snow_depth_cm": 0.0,
        "new_snow_3h_cm": 0.0,
    }
    values.update(weather_overrides)

    assert derive_is_bad_weather(**values) is expected


@pytest.mark.parametrize("field_name", ["origin_gu", "origin_dong", "destination_gu", "destination_dong"])
def test_build_special_vehicle_waiting_time_input_rejects_missing_location_feature(field_name: str) -> None:
    with pytest.raises(WaitingTimeFeatureMappingError, match=field_name):
        build_special_vehicle_waiting_time_input(_source(**{field_name: "  "}))


@pytest.mark.parametrize("field_name", ["origin_gu", "origin_dong", "destination_gu", "destination_dong"])
def test_build_special_vehicle_waiting_time_input_rejects_none_location_feature(field_name: str) -> None:
    with pytest.raises(WaitingTimeFeatureMappingError, match=field_name):
        build_special_vehicle_waiting_time_input(_source(**{field_name: None}))


@pytest.mark.parametrize(
    "weather_overrides",
    [
        {"precipitation_mm": -0.1},
        {"wind_speed_ms": -0.1},
        {"snow_depth_cm": -0.1},
        {"new_snow_3h_cm": -0.1},
    ],
)
def test_build_special_vehicle_waiting_time_input_rejects_invalid_weather(
    weather_overrides: dict[str, float],
) -> None:
    with pytest.raises(WaitingTimeFeatureMappingError):
        build_special_vehicle_waiting_time_input(_source(**weather_overrides))


@pytest.mark.parametrize(
    "source_overrides",
    [
        {"ride_distance_meters": -1},
        {"vehicle_operation_count_prev_day": -1},
        {"purpose": "예약치료"},
        {"requested_at": datetime(2026, 9, 13, 9, 0)},
    ],
)
def test_build_special_vehicle_waiting_time_input_wraps_adapter_validation_errors(
    source_overrides: dict[str, object],
) -> None:
    with pytest.raises(WaitingTimeFeatureMappingError):
        build_special_vehicle_waiting_time_input(_source(**source_overrides))


def test_build_special_vehicle_waiting_time_input_keeps_distance_in_meters_without_km_conversion() -> None:
    prediction_input = build_special_vehicle_waiting_time_input(_source(ride_distance_meters=9876.5))

    assert prediction_input.to_model_features()["승차거리"] == 9876.5
