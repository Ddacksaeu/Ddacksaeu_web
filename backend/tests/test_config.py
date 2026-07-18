from app.core.config import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BACKEND_HOST", "0.0.0.0")
    monkeypatch.setenv("BACKEND_PORT", "9010")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///./configured.db")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.backend_host == "0.0.0.0"
    assert settings.backend_port == 9010
    assert settings.database_url == "sqlite+pysqlite:///./configured.db"
    assert settings.allowed_origins == ["http://localhost:5173", "http://localhost:3000"]
    assert settings.log_level == "DEBUG"


def test_non_development_has_no_default_permissive_cors() -> None:
    settings = Settings(app_env="production")

    assert settings.allowed_origins == []
