from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import jwt

from app.config import get_settings
from app.errors import service_unavailable
from app.models import Room, RoomMember, User
from app.security import generate_token

VIDEO_GRANT = "video"


def livekit_room_name(room: Room) -> str:
    return f"securechat-{room.id}"


def normalize_livekit_url(url: str) -> str:
    cleaned = (url or "").strip()
    if cleaned.startswith("https://"):
        return "wss://" + cleaned[len("https://") :]
    if cleaned.startswith("http://"):
        return "ws://" + cleaned[len("http://") :]
    return cleaned


def livekit_url_is_valid(url: str) -> bool:
    parsed = urlparse(normalize_livekit_url(url))
    return parsed.scheme in {"ws", "wss"} and bool(parsed.netloc)


def is_loopback_url(url: str) -> bool:
    host = urlparse(normalize_livekit_url(url)).hostname or ""
    return host in {"127.0.0.1", "localhost", "0.0.0.0", "::1"}


def client_livekit_url() -> str:
    settings = get_settings()
    public_url = normalize_livekit_url(settings.livekit_public_url)
    if livekit_url_is_valid(public_url):
        return public_url
    return normalize_livekit_url(settings.livekit_url)


def create_access_token(room: Room, user: User, membership: RoomMember) -> dict:
    settings = get_settings()
    if room.status != "active":
        raise service_unavailable("الغرفة مغلقة ولا يمكن إصدار رمز وسائط")
    if membership.status != "active":
        raise service_unavailable("العضوية غير نشطة ولا يمكن إصدار رمز وسائط")
    if not settings.livekit_configured:
        raise service_unavailable("خادم الوسائط غير مُعد على الخادم.")

    url = client_livekit_url()
    if not livekit_url_is_valid(url):
        raise service_unavailable("تعذر تجهيز عنوان خادم الوسائط. تحقق من إعداد LiveKit على الخادم.")

    now = datetime.now(timezone.utc)
    expires_in = max(60, settings.livekit_token_ttl_seconds)
    payload = {
        "iss": settings.livekit_api_key.strip(),
        "sub": user.id,
        "jti": generate_token(12),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "name": membership.display_name,
        VIDEO_GRANT: {
            "roomJoin": True,
            "room": livekit_room_name(room),
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
            "canUpdateOwnMetadata": True,
        },
    }
    token = jwt.encode(
        payload,
        settings.livekit_api_secret.strip(),
        algorithm="HS256",
        headers={"typ": "JWT", "kid": settings.livekit_api_key.strip()},
    )
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return {
        "url": url,
        "token": token,
        "room_name": livekit_room_name(room),
        "identity": user.id,
        "expires_in": expires_in,
    }


def media_status() -> tuple[bool, str, str | None]:
    settings = get_settings()
    url = client_livekit_url()
    if settings.livekit_configured and livekit_url_is_valid(url):
        if is_loopback_url(url) and settings.webrtc_fallback:
            return True, "webrtc", "خادم LiveKit على عنوان محلي غير قابل للوصول من المتصفح. يتم استخدام اتصال الند للند."
        return True, "livekit", None
    if settings.livekit_configured:
        if settings.webrtc_fallback:
            return True, "webrtc", "عنوان خادم LiveKit غير صالح. يتم استخدام اتصال الند للند."
        return False, "none", "عنوان خادم الوسائط غير صالح."
    if settings.webrtc_fallback:
        return True, "webrtc", None
    return False, "none", "خادم الوسائط غير مُعد على الخادم."
