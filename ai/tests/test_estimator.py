from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import ai.waiting_time.estimator as estimator_module
from ai.waiting_time.estimator import (
    MODEL_FEATURE_COLUMNS,
    OUT_OF_TRAINING_TARGET_RANGE_WARNING,
    WAITING_TIME_UNIT,
    WaitingTimeModelUnavailableError,
    WaitingTimePredictionAdapter,
    WaitingTimeInvalidOutputError,
    WaitingTimePredictionInput,
    estimate_waiting_minutes,
    estimate_waiting_minutes_for_input,
    map_prediction_output_to_waiting_time,
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


def test_prediction_input_normalizes_requested_at_to_seoul_time() -> None:
    prediction_input = _prediction_input(
        requested_at=datetime(2026, 9, 13, 0, 30, tzinfo=ZoneInfo("UTC"))
    )

    features = prediction_input.to_model_features()

    assert features["hour"] == 9
    assert features["month"] == 9
    assert features["dayofweek"] == 6


def test_prediction_input_rejects_out_of_serving_hours_after_timezone_normalization() -> None:
    with pytest.raises(ValueError, match="02:00~06:59"):
        _prediction_input(requested_at=datetime(2026, 9, 12, 18, 0, tzinfo=ZoneInfo("UTC")))


def test_prediction_input_rejects_unsupported_category() -> None:
    with pytest.raises(ValueError, match="지원하지 않는 이용목적"):
        _prediction_input(purpose="예약치료")


def test_prediction_input_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _prediction_input(requested_at=datetime(2026, 9, 13, 14, 30))


@pytest.mark.parametrize(
    ("field_name", "expected_message"),
    [
        ("precipitation_mm", "precipitation_mm은 0 이상"),
        ("wind_speed_ms", "wind_speed_ms는 0 이상"),
        ("snow_depth_cm", "snow_depth_cm은 0 이상"),
    ],
)
def test_prediction_input_rejects_negative_weather_features(
    field_name: str,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        _prediction_input(**{field_name: -0.1})


class _FakeWaitingTimeModel:
    def __init__(self, raw_prediction: object = [15.5]) -> None:
        self.raw_prediction = raw_prediction
        self.seen_input: object | None = None

    def predict(self, model_input: object) -> object:
        self.seen_input = model_input
        return self.raw_prediction


def test_prediction_adapter_calls_model_with_training_features_and_returns_waiting_time(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib placeholder")
    fake_model = _FakeWaitingTimeModel([15.5])
    seen_loader_paths: list[Path] = []

    def fake_loader(path: Path) -> _FakeWaitingTimeModel:
        seen_loader_paths.append(path)
        return fake_model

    def fake_model_input_builder(features: dict[str, object]) -> list[dict[str, object]]:
        return [features]

    monkeypatch.setattr(estimator_module, "_build_model_input", fake_model_input_builder)

    adapter = WaitingTimePredictionAdapter(
        model_path=model_path,
        model_name="test_rf_model",
        model_loader=fake_loader,
    )

    estimate = adapter.estimate(_prediction_input())

    assert seen_loader_paths == [model_path]
    assert fake_model.seen_input == [_prediction_input().to_model_features()]
    assert estimate.waitingTime == 15.5
    assert estimate.expected_minutes == 15.5
    assert estimate.model_name == "test_rf_model"
    assert estimate.hour_of_day == 14


def test_prediction_adapter_reuses_lazy_loaded_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib placeholder")
    fake_model = _FakeWaitingTimeModel([10.0])
    load_count = 0

    def fake_loader(path: Path) -> _FakeWaitingTimeModel:
        nonlocal load_count
        load_count += 1
        return fake_model

    monkeypatch.setattr(estimator_module, "_build_model_input", lambda features: [features])

    adapter = WaitingTimePredictionAdapter(model_path=model_path, model_loader=fake_loader)

    adapter.estimate(_prediction_input())
    adapter.estimate(_prediction_input())

    assert load_count == 1


def test_prediction_input_based_estimator_uses_default_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_estimate = map_prediction_output_to_waiting_time(12.0, hour_of_day=14, model_name="fake")

    class FakeDefaultAdapter:
        def estimate(self, prediction_input: WaitingTimePredictionInput) -> object:
            assert prediction_input.to_model_features()["hour"] == 14
            return fake_estimate

    monkeypatch.setattr(estimator_module, "WaitingTimePredictionAdapter", FakeDefaultAdapter)

    assert estimate_waiting_minutes_for_input(_prediction_input()) == fake_estimate


def test_prediction_input_based_estimator_reuses_default_adapter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib placeholder")
    fake_model = _FakeWaitingTimeModel([10.0])
    load_count = 0

    def fake_loader(path: Path) -> _FakeWaitingTimeModel:
        nonlocal load_count
        load_count += 1
        return fake_model

    monkeypatch.setattr(estimator_module, "_build_model_input", lambda features: [features])
    estimator_module._set_default_adapter_for_testing(
        WaitingTimePredictionAdapter(model_path=model_path, model_loader=fake_loader)
    )

    try:
        estimate_waiting_minutes_for_input(_prediction_input())
        estimate_waiting_minutes_for_input(_prediction_input())
    finally:
        estimator_module._set_default_adapter_for_testing(None)

    assert load_count == 1


def test_prediction_input_based_estimator_accepts_explicit_adapter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib placeholder")
    monkeypatch.setattr(estimator_module, "_build_model_input", lambda features: [features])
    adapter = WaitingTimePredictionAdapter(
        model_path=model_path,
        model_loader=lambda path: _FakeWaitingTimeModel([9.5]),
    )

    estimate = estimate_waiting_minutes_for_input(_prediction_input(), adapter=adapter)

    assert estimate.waitingTime == 9.5


def test_prediction_adapter_rejects_missing_model_artifact(tmp_path: Path) -> None:
    adapter = WaitingTimePredictionAdapter(model_path=tmp_path / "missing.joblib")

    with pytest.raises(WaitingTimeModelUnavailableError, match="artifact가 없습니다"):
        adapter.estimate(_prediction_input())


def test_prediction_adapter_rejects_git_lfs_pointer_artifact(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0000\n"
        "size 1480271962\n"
    )
    adapter = WaitingTimePredictionAdapter(model_path=model_path)

    with pytest.raises(WaitingTimeModelUnavailableError, match="Git LFS pointer"):
        adapter.estimate(_prediction_input())


@pytest.mark.parametrize("raw_prediction", [None, float("nan"), float("inf"), -1.0, "11.25"])
def test_prediction_adapter_raises_prediction_error_for_invalid_model_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    raw_prediction: object,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib placeholder")
    monkeypatch.setattr(estimator_module, "_build_model_input", lambda features: [features])
    adapter = WaitingTimePredictionAdapter(
        model_path=model_path,
        model_loader=lambda path: _FakeWaitingTimeModel(raw_prediction),
    )

    with pytest.raises(WaitingTimeInvalidOutputError):
        adapter.estimate(_prediction_input())


def test_prediction_output_maps_numeric_prediction_to_backend_waiting_time() -> None:
    estimate = map_prediction_output_to_waiting_time(
        11.25,
        hour_of_day=14,
        model_name="rf_wait_time_v2_prev_day_weather_final",
    )

    assert estimate.expected_minutes == 11.25
    assert estimate.waitingTime == 11.25
    assert estimate.hour_of_day == 14
    assert estimate.model_name == "rf_wait_time_v2_prev_day_weather_final"
    assert estimate.to_backend_output() == {
        "waitingTime": 11.25,
        "unit": WAITING_TIME_UNIT,
        "warnings": (),
    }


@pytest.mark.parametrize("raw_prediction", [[11.25], (11.25,), [[11.25]]])
def test_prediction_output_accepts_single_prediction_containers(raw_prediction: object) -> None:
    estimate = map_prediction_output_to_waiting_time(raw_prediction, hour_of_day=9)

    assert estimate.waitingTime == 11.25


def test_prediction_output_accepts_array_like_single_prediction() -> None:
    class ArrayLikePrediction:
        def tolist(self) -> list[float]:
            return [12.5]

    estimate = map_prediction_output_to_waiting_time(ArrayLikePrediction(), hour_of_day=9)

    assert estimate.to_backend_output()["waitingTime"] == 12.5


def test_prediction_output_adds_warning_when_prediction_exceeds_training_domain() -> None:
    estimate = map_prediction_output_to_waiting_time(131.5, hour_of_day=9)

    assert estimate.waitingTime == 131.5
    assert estimate.warnings == (OUT_OF_TRAINING_TARGET_RANGE_WARNING,)


@pytest.mark.parametrize(
    "raw_prediction",
    [
        True,
        "11.25",
        None,
        [],
        [1.0, 2.0],
        float("nan"),
        float("inf"),
        -0.1,
    ],
)
def test_prediction_output_rejects_invalid_model_output(raw_prediction: object) -> None:
    with pytest.raises(ValueError):
        map_prediction_output_to_waiting_time(raw_prediction, hour_of_day=9)


def test_prediction_output_rejects_invalid_hour() -> None:
    with pytest.raises(ValueError, match="hour_of_day"):
        map_prediction_output_to_waiting_time(11.25, hour_of_day=24)
