import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response

from app.config import get_settings

SESSION_COOKIE = "sc_session"
CSRF_COOKIE = "sc_csrf"
CSRF_HEADER = "X-CSRF-Token"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return secrets.token_urlsafe(18)


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def tokens_match(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_token(plain), hashed)


def generate_invite_code() -> str:
    return secrets.token_urlsafe(18)


def invite_prefix(code: str) -> str:
    return code[:6]


def session_expiry() -> datetime:
    settings = get_settings()
    return utcnow() + timedelta(seconds=settings.session_ttl_seconds)


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    settings = get_settings()
    cookie_kwargs = {
        "httponly": True,
        "secure": settings.use_secure_cookies,
        "samesite": settings.cookie_samesite,
        "max_age": settings.session_ttl_seconds,
        "path": "/",
    }
    response.set_cookie(settings.session_cookie_name, session_token, **cookie_kwargs)
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        secure=settings.use_secure_cookies,
        samesite=settings.cookie_samesite,
        max_age=settings.session_ttl_seconds,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    for name in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            name,
            path="/",
            secure=settings.use_secure_cookies,
            samesite=settings.cookie_samesite,
        )


def read_session_token(request: Request) -> str | None:
    settings = get_settings()
    return request.cookies.get(settings.session_cookie_name)


def read_csrf_token(request: Request) -> str | None:
    return request.headers.get(CSRF_HEADER) or request.cookies.get(get_settings().csrf_cookie_name)


def mask_invite_code(code: str) -> str:
    if len(code) <= 8:
        return code[:2] + "****"
    return f"{code[:4]}…{code[-2:]}"
