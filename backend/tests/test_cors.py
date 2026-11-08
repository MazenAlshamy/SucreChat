import pytest

from app.config import get_settings
from app.main import _validate_cors_origins


def test_production_rejects_wildcard(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError):
        _validate_cors_origins()

    get_settings.cache_clear()


def test_empty_origins_fallback_in_development(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CORS_ORIGINS", "")
    get_settings.cache_clear()
    assert _validate_cors_origins() == ["http://localhost:5173"]
    get_settings.cache_clear()


def test_empty_origins_allowed_in_production_for_same_origin(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "")
    get_settings.cache_clear()
    assert _validate_cors_origins() == []
    get_settings.cache_clear()


def test_public_origin_is_merged_into_cors(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://app.example/")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://securechat.onrender.com")
    get_settings.cache_clear()
    assert _validate_cors_origins() == [
        "https://app.example",
        "https://securechat.onrender.com",
    ]
    get_settings.cache_clear()
