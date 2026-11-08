import jwt

from fastapi.testclient import TestClient

from app.config import get_settings
from tests.conftest import create_room, csrf_headers, other_client


def _enable_livekit(monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://livekit.example")
    monkeypatch.setenv("LIVEKIT_API_KEY", "devkey")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "devsecret")
    get_settings.cache_clear()


def test_unapproved_user_cannot_get_livekit_token(client: TestClient) -> None:
    created = create_room(client).json()
    guest = other_client()
    guest.post(
        "/api/join-requests",
        json={"code": created["invitations"][0]["code"], "display_name": "سارة"},
        headers=csrf_headers(guest),
    )
    response = guest.post(
        f"/api/rooms/{created['room']['id']}/livekit-token",
        headers=csrf_headers(guest),
    )
    assert response.status_code == 403


def test_foreign_room_member_cannot_get_livekit_token(client: TestClient) -> None:
    first = create_room(client, name="غرفة أولى").json()
    second_owner = other_client()
    second = create_room(second_owner, name="غرفة ثانية", display_name="مالك آخر").json()
    guest = other_client()
    join = guest.post(
        "/api/join-requests",
        json={"code": first["invitations"][0]["code"], "display_name": "عضو"},
        headers=csrf_headers(guest),
    ).json()
    client.post(
        f"/api/join-requests/{join['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    denied = guest.post(
        f"/api/rooms/{second['room']['id']}/livekit-token",
        headers=csrf_headers(guest),
    )
    allowed_without_config = guest.post(
        f"/api/rooms/{first['room']['id']}/livekit-token",
        headers=csrf_headers(guest),
    )
    assert denied.status_code == 403
    assert allowed_without_config.status_code == 503


def test_member_token_requires_livekit_config(client: TestClient) -> None:
    created = create_room(client).json()
    response = client.post(
        f"/api/rooms/{created['room']['id']}/livekit-token",
        headers=csrf_headers(client),
    )
    meeting = client.get(f"/api/rooms/{created['room']['id']}/meeting")
    assert response.status_code == 503
    assert meeting.json()["media_enabled"] is True
    assert meeting.json()["media_provider"] == "webrtc"


def test_approved_member_receives_livekit_token(client: TestClient, monkeypatch) -> None:
    _enable_livekit(monkeypatch)
    created = create_room(client).json()
    room_id = created["room"]["id"]
    code = created["invitations"][0]["code"]
    guest = other_client()
    join = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "سارة"},
        headers=csrf_headers(guest),
    ).json()
    client.post(
        f"/api/join-requests/{join['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )

    meeting = guest.get(f"/api/rooms/{room_id}/meeting")
    assert meeting.status_code == 200
    assert meeting.json()["media_enabled"] is True
    assert meeting.json()["media_provider"] == "livekit"

    session = guest.get("/api/session").json()
    response = guest.post(f"/api/rooms/{room_id}/livekit-token", headers=csrf_headers(guest))
    assert response.status_code == 200
    payload = response.json()
    assert payload["url"] == "wss://livekit.example"
    assert payload["room_name"] == f"securechat-{room_id}"
    assert payload["identity"] == session["user"]["id"]
    claims = jwt.decode(payload["token"], "devsecret", algorithms=["HS256"])
    assert claims["sub"] == session["user"]["id"]
    assert claims["iss"] == "devkey"
    assert claims["name"] == "سارة"
    assert claims["video"]["roomJoin"] is True
    assert claims["video"]["room"] == f"securechat-{room_id}"
    assert claims["video"]["canPublish"] is True
    assert claims["video"]["canSubscribe"] is True
    assert claims["video"]["canPublishData"] is True
    assert "jti" in claims
    assert "iat" in claims


def test_stranger_cannot_get_livekit_token(client: TestClient, monkeypatch) -> None:
    _enable_livekit(monkeypatch)
    created = create_room(client).json()
    stranger = other_client()
    stranger.post("/api/session", json={"display_name": "غريب"}, headers=csrf_headers(stranger))
    response = stranger.post(
        f"/api/rooms/{created['room']['id']}/livekit-token",
        headers=csrf_headers(stranger),
    )
    assert response.status_code == 403


def test_closed_room_cannot_issue_livekit_token(client: TestClient, monkeypatch) -> None:
    _enable_livekit(monkeypatch)
    created = create_room(client).json()
    room_id = created["room"]["id"]
    client.post(f"/api/rooms/{room_id}/close", headers=csrf_headers(client))
    response = client.post(f"/api/rooms/{room_id}/livekit-token", headers=csrf_headers(client))
    assert response.status_code == 503


def test_https_livekit_url_is_normalized_to_wss(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "https://livekit.example")
    monkeypatch.setenv("LIVEKIT_API_KEY", "devkey")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "devsecret")
    get_settings.cache_clear()
    created = create_room(client).json()
    response = client.post(
        f"/api/rooms/{created['room']['id']}/livekit-token",
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["url"] == "wss://livekit.example"


def test_media_disabled_when_fallback_off_and_livekit_missing(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WEBRTC_FALLBACK", "false")
    get_settings.cache_clear()
    created = create_room(client).json()
    meeting = client.get(f"/api/rooms/{created['room']['id']}/meeting")
    token = client.post(
        f"/api/rooms/{created['room']['id']}/livekit-token",
        headers=csrf_headers(client),
    )
    assert meeting.json()["media_enabled"] is False
    assert meeting.json()["media_provider"] == "none"
    assert token.status_code == 503


def test_loopback_livekit_falls_back_to_webrtc(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "ws://127.0.0.1:7880")
    monkeypatch.setenv("LIVEKIT_API_KEY", "devkey")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "devsecret")
    get_settings.cache_clear()
    created = create_room(client).json()
    meeting = client.get(f"/api/rooms/{created['room']['id']}/meeting")
    token = client.post(
        f"/api/rooms/{created['room']['id']}/livekit-token",
        headers=csrf_headers(client),
    )
    assert meeting.json()["media_provider"] == "webrtc"
    assert token.status_code == 200
    assert token.json()["url"] == "ws://127.0.0.1:7880"


def test_invalid_livekit_url_is_rejected(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "not-a-url")
    monkeypatch.setenv("LIVEKIT_API_KEY", "devkey")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "devsecret")
    get_settings.cache_clear()
    created = create_room(client).json()
    meeting = client.get(f"/api/rooms/{created['room']['id']}/meeting")
    token = client.post(
        f"/api/rooms/{created['room']['id']}/livekit-token",
        headers=csrf_headers(client),
    )
    assert meeting.json()["media_enabled"] is True
    assert meeting.json()["media_provider"] == "webrtc"
    assert token.status_code == 503
