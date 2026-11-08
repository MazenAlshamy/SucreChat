import pytest
from pydantic import ValidationError

from app.config import Settings


def test_cors_origin_list_splits_and_trims_values() -> None:
    settings = Settings(
        app_env="development",
        cors_origins="http://localhost:5173, http://127.0.0.1:5173",
    )

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_invalid_app_env_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="staging")


def test_production_flag() -> None:
    settings = Settings(app_env="production", cors_origins="https://securechat.example")

    assert settings.is_production is True


def test_livekit_configured_requires_all_values() -> None:
    empty = Settings(app_env="test")
    partial = Settings(app_env="test", livekit_url="wss://livekit.example", livekit_api_key="key")
    ready = Settings(
        app_env="test",
        livekit_url="wss://livekit.example",
        livekit_api_key="key",
        livekit_api_secret="secret",
    )
    assert empty.livekit_configured is False
    assert partial.livekit_configured is False
    assert ready.livekit_configured is True


def test_webrtc_fallback_enabled_by_default() -> None:
    settings = Settings(app_env="test")
    assert settings.webrtc_fallback is True


def test_secure_cookies_default_in_production() -> None:
    settings = Settings(app_env="production", cors_origins="https://example.com")
    assert settings.use_secure_cookies is True
    assert settings.cookie_samesite == "lax"


def test_livekit_url_normalization() -> None:
    from app.services.livekit import livekit_url_is_valid, normalize_livekit_url

    assert normalize_livekit_url("https://lk.example") == "wss://lk.example"
    assert normalize_livekit_url("http://localhost:7880") == "ws://localhost:7880"
    assert livekit_url_is_valid("wss://lk.example") is True
    assert livekit_url_is_valid("not-a-url") is False
