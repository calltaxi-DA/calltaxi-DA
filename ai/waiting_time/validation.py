"""Prediction result validation for the calltaxi waiting-time model."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ai.waiting_time.estimator import (
    DEFAULT_MODEL_METADATA_PATH,
    DEFAULT_MODEL_NAME,
    OUT_OF_TRAINING_TARGET_RANGE_WARNING,
    SUPPORTED_MODEL_GROUPS,
    WAITING_TIME_UNIT,
    WaitingTimeEstimate,
    WaitingTimePredictionAdapter,
    WaitingTimePredictionInput,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METADATA_PATH = DEFAULT_MODEL_METADATA_PATH
DEFAULT_VALIDATION_OUTPUT_PATH = (
    REPOSITORY_ROOT / "analysis" / "waiting_time" / "prediction_validation_phase4.json"
)
SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class PredictionValidationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class PredictionValidationResult:
    model_group: str
    expected_minutes: float | None
    unit: str
    warnings: tuple[str, ...]
    valid: bool
    issues: tuple[PredictionValidationIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "model_group": self.model_group,
            "expected_minutes": self.expected_minutes,
            "unit": self.unit,
            "warnings": list(self.warnings),
            "valid": self.valid,
            "issues": [issue.__dict__ for issue in self.issues],
        }


@dataclass(frozen=True)
class ExistingAnalysisBaseline:
    model_group: str
    target: str
    count: int
    mean_minutes: float
    median_minutes: float
    p75_minutes: float
    p90_minutes: float
    p95_minutes: float
    source: str

    def compare(self, expected_minutes: float | None) -> dict[str, object]:
        if expected_minutes is None or not math.isfinite(expected_minutes):
            return {
                "status": "invalid_prediction",
                "delta_from_median_minutes": None,
                "delta_from_mean_minutes": None,
                "position": None,
            }

        if expected_minutes < self.median_minutes:
            status = "below_median"
        elif expected_minutes <= self.p90_minutes:
            status = "within_median_to_p90_range"
        elif expected_minutes <= self.p95_minutes:
            status = "between_p90_and_p95_check_if_context_expected"
        else:
            status = "above_p95_requires_review"

        return {
            "status": status,
            "delta_from_median_minutes": expected_minutes - self.median_minutes,
            "delta_from_mean_minutes": expected_minutes - self.mean_minutes,
            "position": {
                "median_minutes": self.median_minutes,
                "p75_minutes": self.p75_minutes,
                "p90_minutes": self.p90_minutes,
                "p95_minutes": self.p95_minutes,
            },
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "model_group": self.model_group,
            "target": self.target,
            "count": self.count,
            "mean_minutes": self.mean_minutes,
            "median_minutes": self.median_minutes,
            "p75_minutes": self.p75_minutes,
            "p90_minutes": self.p90_minutes,
            "p95_minutes": self.p95_minutes,
            "source": self.source,
        }


EXISTING_ANALYSIS_BASELINES = {
    "임차택시_바로콜": ExistingAnalysisBaseline(
        model_group="임차택시_바로콜",
        target="접수→승차",
        count=305_729,
        mean_minutes=42.45,
        median_minutes=28.51,
        p75_minutes=50.28,
        p90_minutes=87.34,
        p95_minutes=145.05,
        source="analysis/waiting_time/usage_pattern_evidence.md",
    ),
    "특장차_바로콜": ExistingAnalysisBaseline(
        model_group="특장차_바로콜",
        target="접수→승차",
        count=1_099_084,
        mean_minutes=46.27,
        median_minutes=33.42,
        p75_minutes=57.33,
        p90_minutes=95.13,
        p95_minutes=133.94,
        source="analysis/waiting_time/usage_pattern_evidence.md",
    ),
}


def sample_prediction_input(model_group: str) -> WaitingTimePredictionInput:
    """Return the reviewed Phase 4 sample input used for smoke validation."""

    return WaitingTimePredictionInput(
        requested_at=datetime(2026, 9, 14, 9, 0, tzinfo=SEOUL_TIMEZONE),
        purpose="치료",
        ride_distance_meters=12_500,
        origin_gu="중구",
        origin_dong="명동",
        destination_gu="강남구",
        destination_dong="역삼동",
        movement_type="구 간 이동",
        model_group=model_group,
        vehicle_operation_count_prev_day=412,
        temperature_c=23.5,
        precipitation_mm=0,
        wind_speed_ms=2.1,
        snow_depth_cm=0,
        is_bad_weather=False,
    )


def validate_prediction_estimate(
    estimate: WaitingTimeEstimate,
    *,
    model_group: str,
    training_target_max_minutes: float,
) -> PredictionValidationResult:
    """Validate model output type, unit, finite value, and training-domain warnings."""

    issues: list[PredictionValidationIssue] = []
    expected_minutes = estimate.expected_minutes
    if expected_minutes is None:
        issues.append(PredictionValidationIssue("null", "expected_minutes must not be null"))
        expected_minutes_value = None
    elif isinstance(expected_minutes, bool) or not isinstance(expected_minutes, (int, float)):
        issues.append(PredictionValidationIssue("invalid_type", "expected_minutes must be numeric minutes"))
        expected_minutes_value: float | None = None
    else:
        expected_minutes_value = float(expected_minutes)
        if not math.isfinite(expected_minutes_value):
            issues.append(PredictionValidationIssue("non_finite", "expected_minutes must be finite"))
        elif expected_minutes_value < 0:
            issues.append(PredictionValidationIssue("negative", "expected_minutes must be non-negative"))

    if WAITING_TIME_UNIT != "minutes":
        issues.append(PredictionValidationIssue("invalid_unit", "waiting-time output unit must be minutes"))

    if (
        expected_minutes_value is not None
        and math.isfinite(expected_minutes_value)
        and expected_minutes_value > training_target_max_minutes
        and OUT_OF_TRAINING_TARGET_RANGE_WARNING not in estimate.warnings
    ):
        issues.append(
            PredictionValidationIssue(
                "missing_out_of_range_warning",
                "prediction above training target max must carry an out-of-range warning",
            )
        )

    return PredictionValidationResult(
        model_group=model_group,
        expected_minutes=expected_minutes_value,
        unit=WAITING_TIME_UNIT,
        warnings=estimate.warnings,
        valid=not issues,
        issues=tuple(issues),
    )


def run_sample_prediction_validation(
    *,
    adapter: WaitingTimePredictionAdapter | None = None,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> dict[str, object]:
    """Run sample predictions for both model groups and return a validation report."""

    active_adapter = adapter or WaitingTimePredictionAdapter()
    metadata = _read_metadata(metadata_path)
    training_target_max_minutes = float(
        metadata["prediction_domain"]["training_target_max_minutes"]  # type: ignore[index]
    )
    results = [
        validate_prediction_estimate(
            active_adapter.estimate(sample_prediction_input(model_group)),
            model_group=model_group,
            training_target_max_minutes=training_target_max_minutes,
        )
        for model_group in SUPPORTED_MODEL_GROUPS
    ]
    expected_values = [result.expected_minutes for result in results if result.expected_minutes is not None]
    conservative_expected_minutes = max(expected_values) if expected_values else None
    warnings = sorted({warning for result in results for warning in result.warnings})
    baseline_comparisons = {
        result.model_group: {
            "baseline": EXISTING_ANALYSIS_BASELINES[result.model_group].to_dict(),
            "comparison": EXISTING_ANALYSIS_BASELINES[result.model_group].compare(result.expected_minutes),
        }
        for result in results
    }
    return {
        "schema_version": "1.0",
        "validated_at": datetime.now(SEOUL_TIMEZONE).isoformat(),
        "model_name": DEFAULT_MODEL_NAME,
        "target": metadata["target_col"],
        "unit": WAITING_TIME_UNIT,
        "sample_input": sample_prediction_input(SUPPORTED_MODEL_GROUPS[0]).to_model_features()
        | {"model_group_policy": "predict_both_and_use_max"},
        "results": [result.to_dict() for result in results],
        "conservative_expected_minutes": conservative_expected_minutes,
        "conservative_expected_seconds": (
            round(conservative_expected_minutes * 60) if conservative_expected_minutes is not None else None
        ),
        "all_outputs_valid": all(result.valid for result in results),
        "comparison_to_existing_analysis": {
            "baseline_source": "analysis/waiting_time/usage_pattern_evidence.md",
            "baseline_target": "접수→승차",
            "baseline_comparisons": baseline_comparisons,
            "reported_test_MAE": metadata["reported_test_MAE"],
            "reported_test_RMSE": metadata["reported_test_RMSE"],
            "reported_test_R2": metadata["reported_test_R2"],
            "training_target_max_minutes": training_target_max_minutes,
            "prediction_over_130_policy": metadata["prediction_domain"]["prediction_over_130_policy"],  # type: ignore[index]
            "sample_status": _sample_status(
                conservative_expected_minutes=conservative_expected_minutes,
                training_target_max_minutes=training_target_max_minutes,
                warnings=warnings,
            ),
        },
    }


def write_validation_report(
    output_path: Path = DEFAULT_VALIDATION_OUTPUT_PATH,
    *,
    adapter: WaitingTimePredictionAdapter | None = None,
) -> dict[str, object]:
    report = run_sample_prediction_validation(adapter=adapter)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _sample_status(
    *,
    conservative_expected_minutes: float | None,
    training_target_max_minutes: float,
    warnings: list[str],
) -> str:
    if conservative_expected_minutes is None:
        return "invalid_no_prediction"
    if OUT_OF_TRAINING_TARGET_RANGE_WARNING in warnings:
        return "valid_with_out_of_training_target_range_warning"
    if conservative_expected_minutes <= training_target_max_minutes:
        return "valid_within_training_target_range"
    return "invalid_missing_out_of_training_target_range_warning"


def _read_metadata(metadata_path: Path) -> dict[str, Any]:
    with metadata_path.open(encoding="utf-8") as file:
        metadata = json.load(file)
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a JSON object")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate calltaxi waiting-time prediction output.")
    parser.add_argument("--output", type=Path, default=DEFAULT_VALIDATION_OUTPUT_PATH)
    args = parser.parse_args()
    report = write_validation_report(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
