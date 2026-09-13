from pathlib import Path

import pytest

from app.core.config import ROOT_ENV_PATH, Settings


def test_settings_use_repository_root_env_independent_of_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert ROOT_ENV_PATH == Path(__file__).resolve().parents[2] / ".env"
    assert Settings.model_config["env_file"] == ROOT_ENV_PATH


def test_settings_accepts_tmap_app_key_alias(monkeypatch) -> None:
    monkeypatch.delenv("APP_TMAP_APP_KEY", raising=False)
    monkeypatch.setenv("TMAP_APP_KEY", "alias-test-key")

    settings = Settings()

    assert settings.tmap_app_key == "alias-test-key"


def test_settings_prefers_app_tmap_app_key_over_alias(monkeypatch) -> None:
    monkeypatch.setenv("APP_TMAP_APP_KEY", "preferred-test-key")
    monkeypatch.setenv("TMAP_APP_KEY", "alias-test-key")

    settings = Settings()

    assert settings.tmap_app_key == "preferred-test-key"


def test_settings_accepts_odsay_api_key_alias(monkeypatch) -> None:
    monkeypatch.delenv("APP_ODSAY_API_KEY", raising=False)
    monkeypatch.setenv("ODSAY_API_KEY", "alias-odsay-key")

    settings = Settings()

    assert settings.odsay_api_key == "alias-odsay-key"


def test_settings_prefers_app_odsay_api_key_over_alias(monkeypatch) -> None:
    monkeypatch.setenv("APP_ODSAY_API_KEY", "preferred-odsay-key")
    monkeypatch.setenv("ODSAY_API_KEY", "alias-odsay-key")

    settings = Settings()

    assert settings.odsay_api_key == "preferred-odsay-key"
