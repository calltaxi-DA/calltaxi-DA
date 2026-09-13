"""Runtime/environment checks for the calltaxi waiting-time prediction model."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai.waiting_time.estimator import (
    DEFAULT_MODEL_METADATA_PATH,
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_PATH,
    MODEL_FEATURE_COLUMNS,
    MODEL_METADATA_PATH_ENV_VAR,
    MODEL_PATH_ENV_VAR,
    WAITING_TIME_UNIT,
    WaitingTimeModelUnavailableError,
    _is_git_lfs_pointer,
)

SUPPORTED_PYTHON_MAJOR_MINOR = (3, 12)
REQUIRED_RUNTIME_DEPENDENCIES = (
    ("joblib", "joblib", "1.4.2"),
    ("pandas", "pandas", "2.2.3"),
    ("sklearn", "scikit-learn", "1.9.0"),
)


@dataclass(frozen=True)
class RuntimeCheckItem:
    name: str
    ok: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "message": self.message,
        }


@dataclass(frozen=True)
class WaitingTimeRuntimeReport:
    python_version: str
    required_python: str
    model_name: str
    model_path: str
    metadata_path: str
    env_vars: dict[str, str]
    checks: tuple[RuntimeCheckItem, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "python_version": self.python_version,
            "required_python": self.required_python,
            "model_name": self.model_name,
            "model_path": self.model_path,
            "metadata_path": self.metadata_path,
            "env_vars": self.env_vars,
            "checks": [check.to_dict() for check in self.checks],
        }


def check_waiting_time_runtime(
    *,
    model_path: Path = DEFAULT_MODEL_PATH,
    metadata_path: Path = DEFAULT_MODEL_METADATA_PATH,
) -> WaitingTimeRuntimeReport:
    """Return whether the current environment can load the reviewed model artifact."""

    checks = [
        _check_python_version(),
        *_check_runtime_dependencies(),
        _check_model_artifact(model_path),
        _check_model_metadata(metadata_path),
    ]

    return WaitingTimeRuntimeReport(
        python_version=_python_version_label(),
        required_python=_required_python_label(),
        model_name=DEFAULT_MODEL_NAME,
        model_path=str(model_path),
        metadata_path=str(metadata_path),
        env_vars={
            MODEL_PATH_ENV_VAR: str(model_path),
            MODEL_METADATA_PATH_ENV_VAR: str(metadata_path),
        },
        checks=tuple(checks),
    )


def _check_python_version() -> RuntimeCheckItem:
    current = sys.version_info[:2]
    required = SUPPORTED_PYTHON_MAJOR_MINOR
    if current == required:
        return RuntimeCheckItem(
            name="python_version",
            ok=True,
            message=f"Python {_python_version_label()} matches required {_required_python_label()}",
        )
    return RuntimeCheckItem(
        name="python_version",
        ok=False,
        message=f"Python {_python_version_label()} does not match required {_required_python_label()}",
    )


def _check_runtime_dependencies() -> tuple[RuntimeCheckItem, ...]:
    checks: list[RuntimeCheckItem] = []
    for import_name, distribution_name, required_version in REQUIRED_RUNTIME_DEPENDENCIES:
        if importlib.util.find_spec(import_name) is None:
            checks.append(
                RuntimeCheckItem(
                    name=f"dependency:{distribution_name}",
                    ok=False,
                    message=f"{distribution_name} is not installed",
                )
            )
            continue

        try:
            installed_version = importlib.metadata.version(distribution_name)
        except importlib.metadata.PackageNotFoundError:
            checks.append(
                RuntimeCheckItem(
                    name=f"dependency:{distribution_name}",
                    ok=False,
                    message=f"{distribution_name} distribution metadata is not available",
                )
            )
            continue

        checks.append(
            RuntimeCheckItem(
                name=f"dependency:{distribution_name}",
                ok=installed_version == required_version,
                message=(
                    f"{distribution_name}=={installed_version}; "
                    f"required {distribution_name}=={required_version}"
                ),
            )
        )
    return tuple(checks)


def _check_model_artifact(model_path: Path) -> RuntimeCheckItem:
    if not model_path.exists():
        return RuntimeCheckItem(
            name="model_artifact",
            ok=False,
            message=f"model artifact is missing: {model_path}",
        )
    try:
        if _is_git_lfs_pointer(model_path):
            return RuntimeCheckItem(
                name="model_artifact",
                ok=False,
                message=(
                    "model artifact is a Git LFS pointer; run "
                    f'git lfs pull --include="{_display_path(model_path)}"'
                ),
            )
    except (OSError, ValueError, WaitingTimeModelUnavailableError) as exc:
        return RuntimeCheckItem(
            name="model_artifact",
            ok=False,
            message=f"model artifact cannot be read: {exc}",
        )

    return RuntimeCheckItem(
        name="model_artifact",
        ok=True,
        message=f"model artifact is available: {model_path}",
    )


def _check_model_metadata(metadata_path: Path) -> RuntimeCheckItem:
    if not metadata_path.exists():
        return RuntimeCheckItem(
            name="model_metadata",
            ok=False,
            message=f"model metadata is missing: {metadata_path}",
        )

    try:
        metadata = _read_json_object(metadata_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return RuntimeCheckItem(
            name="model_metadata",
            ok=False,
            message=f"model metadata cannot be read: {exc}",
        )

    if metadata.get("target_unit") != WAITING_TIME_UNIT:
        return RuntimeCheckItem(
            name="model_metadata",
            ok=False,
            message=f"metadata target_unit must be {WAITING_TIME_UNIT}",
        )

    if tuple(metadata.get("features", ())) != MODEL_FEATURE_COLUMNS:
        return RuntimeCheckItem(
            name="model_metadata",
            ok=False,
            message="metadata feature list does not match adapter feature columns",
        )

    created_at = metadata.get("created_at", "unknown")
    return RuntimeCheckItem(
        name="model_metadata",
        ok=True,
        message=f"metadata is valid; created_at={created_at}",
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("metadata must be a JSON object")
    return data


def _python_version_label() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _required_python_label() -> str:
    major, minor = SUPPORTED_PYTHON_MAJOR_MINOR
    return f"{major}.{minor}.x"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check waiting-time model runtime environment.")
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--metadata-path", type=Path, default=DEFAULT_MODEL_METADATA_PATH)
    args = parser.parse_args()

    report = check_waiting_time_runtime(
        model_path=args.model_path,
        metadata_path=args.metadata_path,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if not report.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
