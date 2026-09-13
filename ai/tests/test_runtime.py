import json
from collections import namedtuple
from pathlib import Path

import pytest

import ai.waiting_time.estimator as estimator_module
import ai.waiting_time.runtime as runtime_module
from ai.waiting_time.estimator import MODEL_FEATURE_COLUMNS, MODEL_PATH_ENV_VAR
from ai.waiting_time.runtime import check_waiting_time_runtime

_VersionInfo = namedtuple("_VersionInfo", "major minor micro releaselevel serial")


def _metadata_path(tmp_path: Path, **overrides: object) -> Path:
    metadata: dict[str, object] = {
        "target_unit": "minutes",
        "features": list(MODEL_FEATURE_COLUMNS),
        "created_at": "2026-09-13T20:07:44",
    }
    metadata.update(overrides)
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    return path


def test_runtime_check_accepts_ready_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib artifact placeholder")
    metadata_path = _metadata_path(tmp_path)

    monkeypatch.setattr(runtime_module.sys, "version_info", _VersionInfo(3, 12, 4, "final", 0))
    monkeypatch.setattr(runtime_module.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(
        runtime_module.importlib.metadata,
        "version",
        lambda distribution_name: {
            "joblib": "1.4.2",
            "pandas": "2.2.3",
            "scikit-learn": "1.9.0",
        }[distribution_name],
    )

    report = check_waiting_time_runtime(model_path=model_path, metadata_path=metadata_path)

    assert report.ok is True
    assert report.required_python == "3.12.x"
    assert report.model_path == str(model_path)
    assert report.metadata_path == str(metadata_path)
    assert [check.name for check in report.checks] == [
        "python_version",
        "dependency:joblib",
        "dependency:pandas",
        "dependency:scikit-learn",
        "model_artifact",
        "model_metadata",
    ]


def test_runtime_path_resolver_uses_repository_relative_env_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MODEL_PATH_ENV_VAR, "custom/model.joblib")

    resolved = estimator_module._resolve_runtime_path(
        MODEL_PATH_ENV_VAR,
        Path("analysis/waiting_time/default.joblib"),
    )

    assert resolved == estimator_module.REPOSITORY_ROOT / "custom/model.joblib"


def test_runtime_check_reports_git_lfs_pointer_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0000\n"
        "size 1480271962\n",
        encoding="utf-8",
    )
    metadata_path = _metadata_path(tmp_path)
    monkeypatch.setattr(runtime_module, "_check_python_version", lambda: _ok("python_version"))
    monkeypatch.setattr(runtime_module, "_check_runtime_dependencies", lambda: ())

    report = check_waiting_time_runtime(model_path=model_path, metadata_path=metadata_path)

    assert report.ok is False
    artifact_check = next(check for check in report.checks if check.name == "model_artifact")
    assert artifact_check.ok is False
    assert "Git LFS pointer" in artifact_check.message
    assert "git lfs pull" in artifact_check.message


def test_runtime_check_rejects_metadata_feature_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib artifact placeholder")
    metadata_path = _metadata_path(tmp_path, features=["hour"])
    monkeypatch.setattr(runtime_module, "_check_python_version", lambda: _ok("python_version"))
    monkeypatch.setattr(runtime_module, "_check_runtime_dependencies", lambda: ())

    report = check_waiting_time_runtime(model_path=model_path, metadata_path=metadata_path)

    assert report.ok is False
    metadata_check = next(check for check in report.checks if check.name == "model_metadata")
    assert metadata_check.ok is False
    assert "feature list" in metadata_check.message


def test_runtime_check_reports_dependency_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib artifact placeholder")
    metadata_path = _metadata_path(tmp_path)
    monkeypatch.setattr(runtime_module.sys, "version_info", _VersionInfo(3, 12, 4, "final", 0))
    monkeypatch.setattr(runtime_module.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(
        runtime_module.importlib.metadata,
        "version",
        lambda distribution_name: "0.0.0" if distribution_name == "pandas" else {
            "joblib": "1.4.2",
            "scikit-learn": "1.9.0",
        }[distribution_name],
    )

    report = check_waiting_time_runtime(model_path=model_path, metadata_path=metadata_path)

    assert report.ok is False
    pandas_check = next(check for check in report.checks if check.name == "dependency:pandas")
    assert pandas_check.ok is False
    assert "required pandas==2.2.3" in pandas_check.message


def _ok(name: str) -> runtime_module.RuntimeCheckItem:
    return runtime_module.RuntimeCheckItem(name=name, ok=True, message="ok")
