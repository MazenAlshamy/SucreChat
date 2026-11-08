from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "SecureChat"
    app_env: str = "development"
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./securechat.db"
    cors_origins: str = "http://localhost:5173"
    host: str = "0.0.0.0"
    port: int = 8000
    session_cookie_name: str = "sc_session"
    csrf_cookie_name: str = "sc_csrf"
    session_ttl_hours: int = 168
    room_name_min_length: int = 2
    room_name_max_length: int = 80
    room_description_max_length: int = 500
    room_max_participants_default: int = 8
    room_max_participants_min: int = 2
    room_max_participants_limit: int = 50
    display_name_min_length: int = 2
    display_name_max_length: int = 40
    invite_max_uses_limit: int = 1000
    rate_limit_enabled: bool = True
    rate_limit_join_per_minute: int = 10
    rate_limit_invite_lookup_per_minute: int = 30
    rate_limit_room_create_per_minute: int = 8
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_public_url: str = ""
    livekit_token_ttl_seconds: int = 3600
    rate_limit_livekit_per_minute: int = 20
    webrtc_fallback: bool = True
    cookie_secure: bool | None = None
    cookie_samesite: str = "lax"
    public_origin: str = ""
    render_external_url: str = ""
    frontend_dist_dir: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "SecureChat"
    smtp_use_tls: bool = True
    smtp_encryption: str = ""
    email_verification_ttl_seconds: int = 60
    email_verification_max_attempts: int = 5
    rate_limit_register_per_minute: int = 8
    rate_limit_verify_per_minute: int = 10
    rate_limit_resend_per_minute: int = 3
    rate_limit_login_per_minute: int = 10
    chat_message_max_length: int = 1000
    rate_limit_chat_per_minute: int = 30

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("app_env")
    @classmethod
    def normalize_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production")
        return normalized

    @field_validator("cookie_secure", mode="before")
    @classmethod
    def empty_cookie_secure(cls, value):
        if value in ("", None):
            return None
        return value

    @field_validator("cookie_samesite")
    @classmethod
    def normalize_samesite(cls, value: str) -> str:
        normalized = (value or "lax").strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return normalized

    @field_validator(
        "livekit_url",
        "livekit_api_key",
        "livekit_api_secret",
        "livekit_public_url",
        "public_origin",
        "render_external_url",
        "frontend_dist_dir",
        "smtp_host",
        "smtp_username",
        "smtp_from",
        "smtp_from_email",
        "smtp_from_name",
        "smtp_encryption",
        mode="before",
    )
    @classmethod
    def strip_livekit_values(cls, value):
        if value is None:
            return ""
        return str(value).strip()

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]
        for extra in (self.public_origin, self.render_external_url):
            origin = extra.strip().rstrip("/")
            if origin and origin not in origins:
                origins.append(origin)
        return origins

    @property
    def resolved_frontend_dist(self) -> Path:
        raw = self.frontend_dist_dir.strip()
        if raw:
            return Path(raw)
        return BACKEND_DIR.parent / "frontend" / "dist"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def session_ttl_seconds(self) -> int:
        return self.session_ttl_hours * 3600

    @property
    def use_secure_cookies(self) -> bool:
        if self.cookie_samesite == "none":
            return True
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.is_production

    @property
    def livekit_configured(self) -> bool:
        return bool(
            self.livekit_url.strip()
            and self.livekit_api_key.strip()
            and self.livekit_api_secret.strip()
        )

    @property
    def resolved_smtp_from(self) -> str:
        return self.smtp_from.strip() or self.smtp_from_email.strip()

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host.strip() and self.resolved_smtp_from)

    @property
    def smtp_encryption_mode(self) -> str:
        raw = (self.smtp_encryption or "").strip().lower().replace("_", "")
        if raw in {"ssl", "tls", "smtps"}:
            return "ssl"
        if raw in {"starttls"}:
            return "starttls"
        if raw in {"none", "off", "false", "plain"}:
            return "none"
        if self.smtp_port == 465:
            return "ssl"
        if self.smtp_use_tls or self.smtp_port == 587:
            return "starttls"
        return "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()
