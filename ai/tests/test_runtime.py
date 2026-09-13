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
        "model_name": runtime_module.EXPECTED_MODEL_METADATA_MODEL_NAME,
        "target_unit": "minutes",
        "features": list(MODEL_FEATURE_COLUMNS),
        "created_at": runtime_module.EXPECTED_MODEL_METADATA_CREATED_AT,
        "reported_test_MAE": runtime_module.EXPECTED_MODEL_METADATA_REPORTED_TEST_MAE,
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

    monkeypatch.setattr(runtime_module, "EXPECTED_MODEL_ARTIFACT_SIZE_BYTES", model_path.stat().st_size)
    monkeypatch.setattr(runtime_module.sys, "version_info", _VersionInfo(3, 12, 4, "final", 0))
    monkeypatch.setattr(runtime_module.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(
        runtime_module.importlib.metadata,
        "version",
        lambda distribution_name: {
            "joblib": "1.4.2",
            "pandas": "2.2.3",
            "scikit-learn": "1.9.0",
            "numpy": "2.5.2",
            "scipy": "1.18.1",
            "threadpoolctl": "3.6.0",
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
        "dependency:numpy",
        "dependency:scipy",
        "dependency:threadpoolctl",
        "model_artifact_size",
        "model_artifact",
        "model_metadata:model_name",
        "model_metadata:created_at",
        "model_metadata:reported_test_MAE",
        "model_metadata:target_unit",
        "model_metadata:features",
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


def test_runtime_check_rejects_artifact_size_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"different model artifact")
    metadata_path = _metadata_path(tmp_path)
    monkeypatch.setattr(runtime_module, "_check_python_version", lambda: _ok("python_version"))
    monkeypatch.setattr(runtime_module, "_check_runtime_dependencies", lambda: ())
    monkeypatch.setattr(runtime_module, "EXPECTED_MODEL_ARTIFACT_SIZE_BYTES", model_path.stat().st_size + 1)

    report = check_waiting_time_runtime(model_path=model_path, metadata_path=metadata_path)

    assert report.ok is False
    size_check = next(check for check in report.checks if check.name == "model_artifact_size")
    assert size_check.ok is False
    assert "expected" in size_check.message


@pytest.mark.parametrize(
    ("metadata_override", "check_name"),
    [
        ({"model_name": "different model"}, "model_metadata:model_name"),
        ({"created_at": "2026-01-01T00:00:00"}, "model_metadata:created_at"),
        ({"reported_test_MAE": 99.0}, "model_metadata:reported_test_MAE"),
    ],
)
def test_runtime_check_rejects_metadata_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    metadata_override: dict[str, object],
    check_name: str,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"real joblib artifact placeholder")
    metadata_path = _metadata_path(tmp_path, **metadata_override)
    monkeypatch.setattr(runtime_module, "_check_python_version", lambda: _ok("python_version"))
    monkeypatch.setattr(runtime_module, "_check_runtime_dependencies", lambda: ())
    monkeypatch.setattr(runtime_module, "EXPECTED_MODEL_ARTIFACT_SIZE_BYTES", model_path.stat().st_size)

    report = check_waiting_time_runtime(model_path=model_path, metadata_path=metadata_path)

    assert report.ok is False
    metadata_check = next(check for check in report.checks if check.name == check_name)
    assert metadata_check.ok is False


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
    metadata_check = next(check for check in report.checks if check.name == "model_metadata:features")
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
            "numpy": "2.5.2",
            "scipy": "1.18.1",
            "threadpoolctl": "3.6.0",
        }[distribution_name],
    )

    report = check_waiting_time_runtime(model_path=model_path, metadata_path=metadata_path)

    assert report.ok is False
    pandas_check = next(check for check in report.checks if check.name == "dependency:pandas")
    assert pandas_check.ok is False
    assert "required pandas==2.2.3" in pandas_check.message


def test_runtime_check_reports_transitive_dependency_version_mismatch(
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
        lambda distribution_name: "0.0.0" if distribution_name == "numpy" else {
            "joblib": "1.4.2",
            "pandas": "2.2.3",
            "scikit-learn": "1.9.0",
            "scipy": "1.18.1",
            "threadpoolctl": "3.6.0",
        }[distribution_name],
    )
    monkeypatch.setattr(runtime_module, "EXPECTED_MODEL_ARTIFACT_SIZE_BYTES", model_path.stat().st_size)

    report = check_waiting_time_runtime(model_path=model_path, metadata_path=metadata_path)

    assert report.ok is False
    numpy_check = next(check for check in report.checks if check.name == "dependency:numpy")
    assert numpy_check.ok is False
    assert "required numpy==2.5.2" in numpy_check.message


def _ok(name: str) -> runtime_module.RuntimeCheckItem:
    return runtime_module.RuntimeCheckItem(name=name, ok=True, message="ok")
