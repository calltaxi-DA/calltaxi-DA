from app.core.config import Settings


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
