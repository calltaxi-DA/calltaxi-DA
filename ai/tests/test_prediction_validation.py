import json
from pathlib import Path

from ai.waiting_time.estimator import (
    OUT_OF_TRAINING_TARGET_RANGE_WARNING,
    WaitingTimeEstimate,
    WaitingTimePredictionInput,
)
from ai.waiting_time.validation import (
    run_sample_prediction_validation,
    validate_prediction_estimate,
    write_validation_report,
)


class FakeValidationAdapter:
    def __init__(self, values_by_group: dict[str, WaitingTimeEstimate]) -> None:
        self.values_by_group = values_by_group
        self.seen_inputs: list[WaitingTimePredictionInput] = []

    def estimate(self, prediction_input: WaitingTimePredictionInput) -> WaitingTimeEstimate:
        self.seen_inputs.append(prediction_input)
        return self.values_by_group[prediction_input.model_group]


def _metadata_path(tmp_path: Path) -> Path:
    metadata = {
        "target_col": "target_min",
        "reported_test_MAE": 11.105367785137439,
        "reported_test_RMSE": 15.332262378232757,
        "reported_test_R2": 0.6010887068297474,
        "prediction_domain": {
            "training_target_max_minutes": 130,
            "prediction_over_130_policy": "return_prediction_with_out_of_training_target_range_warning",
        },
    }
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    return path


def test_validate_prediction_estimate_accepts_numeric_minutes() -> None:
    result = validate_prediction_estimate(
        WaitingTimeEstimate(expected_minutes=41.2, hour_of_day=9),
        model_group="특장차_바로콜",
        training_target_max_minutes=130,
    )

    assert result.valid is True
    assert result.expected_minutes == 41.2
    assert result.unit == "minutes"
    assert result.issues == ()


def test_validate_prediction_estimate_rejects_nan_and_negative_values() -> None:
    nan_result = validate_prediction_estimate(
        WaitingTimeEstimate(expected_minutes=float("nan"), hour_of_day=9),
        model_group="특장차_바로콜",
        training_target_max_minutes=130,
    )
    negative_result = validate_prediction_estimate(
        WaitingTimeEstimate(expected_minutes=-0.1, hour_of_day=9),
        model_group="특장차_바로콜",
        training_target_max_minutes=130,
    )

    assert nan_result.valid is False
    assert nan_result.issues[0].code == "non_finite"
    assert negative_result.valid is False
    assert negative_result.issues[0].code == "negative"


def test_validate_prediction_estimate_rejects_null_inf_and_non_numeric_values() -> None:
    null_result = validate_prediction_estimate(
        WaitingTimeEstimate(expected_minutes=None, hour_of_day=9),  # type: ignore[arg-type]
        model_group="특장차_바로콜",
        training_target_max_minutes=130,
    )
    inf_result = validate_prediction_estimate(
        WaitingTimeEstimate(expected_minutes=float("inf"), hour_of_day=9),
        model_group="특장차_바로콜",
        training_target_max_minutes=130,
    )
    non_numeric_result = validate_prediction_estimate(
        WaitingTimeEstimate(expected_minutes="41.2", hour_of_day=9),  # type: ignore[arg-type]
        model_group="특장차_바로콜",
        training_target_max_minutes=130,
    )

    assert null_result.valid is False
    assert null_result.issues[0].code == "null"
    assert inf_result.valid is False
    assert inf_result.issues[0].code == "non_finite"
    assert non_numeric_result.valid is False
    assert non_numeric_result.issues[0].code == "invalid_type"


def test_validate_prediction_estimate_requires_out_of_range_warning() -> None:
    missing_warning = validate_prediction_estimate(
        WaitingTimeEstimate(expected_minutes=131.0, hour_of_day=9),
        model_group="특장차_바로콜",
        training_target_max_minutes=130,
    )
    with_warning = validate_prediction_estimate(
        WaitingTimeEstimate(
            expected_minutes=131.0,
            hour_of_day=9,
            warnings=(OUT_OF_TRAINING_TARGET_RANGE_WARNING,),
        ),
        model_group="특장차_바로콜",
        training_target_max_minutes=130,
    )

    assert missing_warning.valid is False
    assert missing_warning.issues[0].code == "missing_out_of_range_warning"
    assert with_warning.valid is True


def test_run_sample_prediction_validation_checks_both_groups_and_conservative_max(tmp_path: Path) -> None:
    adapter = FakeValidationAdapter(
        {
            "임차택시_바로콜": WaitingTimeEstimate(expected_minutes=40.5, hour_of_day=9),
            "특장차_바로콜": WaitingTimeEstimate(expected_minutes=41.2, hour_of_day=9),
        }
    )

    report = run_sample_prediction_validation(adapter=adapter, metadata_path=_metadata_path(tmp_path))

    assert [item.model_group for item in adapter.seen_inputs] == ["임차택시_바로콜", "특장차_바로콜"]
    assert report["all_outputs_valid"] is True
    assert report["conservative_expected_minutes"] == 41.2
    assert report["conservative_expected_seconds"] == 2472
    assert report["comparison_to_existing_analysis"]["sample_status"] == "valid_within_training_target_range"
    comparisons = report["comparison_to_existing_analysis"]["baseline_comparisons"]
    assert comparisons["임차택시_바로콜"]["baseline"]["median_minutes"] == 28.51
    assert comparisons["임차택시_바로콜"]["comparison"]["status"] == "within_median_to_p90_range"
    assert comparisons["특장차_바로콜"]["baseline"]["p90_minutes"] == 95.13
    assert comparisons["특장차_바로콜"]["comparison"]["status"] == "within_median_to_p90_range"


def test_write_validation_report_outputs_json(tmp_path: Path) -> None:
    output_path = tmp_path / "prediction-validation.json"
    adapter = FakeValidationAdapter(
        {
            "임차택시_바로콜": WaitingTimeEstimate(expected_minutes=40.5, hour_of_day=9),
            "특장차_바로콜": WaitingTimeEstimate(expected_minutes=41.2, hour_of_day=9),
        }
    )

    report = write_validation_report(output_path, adapter=adapter)

    assert json.loads(output_path.read_text(encoding="utf-8"))["model_name"] == report["model_name"]
