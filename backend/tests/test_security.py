from fastapi.testclient import TestClient

from app.config import get_settings
from app.rate_limit import reset_rate_limits
from tests.conftest import create_room, csrf_headers, other_client


def test_health_includes_security_headers(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=(self)" in response.headers["permissions-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_authenticated_mutation_requires_csrf(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    response = client.post(f"/api/rooms/{room_id}/close")
    assert response.status_code == 403
    allowed = client.post(f"/api/rooms/{room_id}/close", headers=csrf_headers(client))
    assert allowed.status_code == 200


def test_logout_requires_csrf_when_session_exists(client: TestClient) -> None:
    create_room(client)
    denied = client.delete("/api/session")
    assert denied.status_code == 403
    assert client.get("/api/rooms").status_code == 200


def test_logout_revokes_session_cookie(client: TestClient) -> None:
    create_room(client)
    listed = client.get("/api/rooms")
    assert listed.status_code == 200
    logout = client.delete("/api/session", headers=csrf_headers(client))
    assert logout.status_code == 200
    denied = client.get("/api/rooms")
    assert denied.status_code == 401


def test_pending_user_still_blocked_from_meeting_after_reload(client: TestClient) -> None:
    created = create_room(client).json()
    guest = other_client()
    join = guest.post(
        "/api/join-requests",
        json={"code": created["invitations"][0]["code"], "display_name": "سارة"},
        headers=csrf_headers(guest),
    ).json()
    assert join["status"] == "pending"
    again = guest.get(f"/api/rooms/{created['room']['id']}/meeting")
    token = guest.post(
        f"/api/rooms/{created['room']['id']}/livekit-token",
        headers=csrf_headers(guest),
    )
    assert again.status_code == 403
    assert token.status_code == 403


def test_join_rate_limit_returns_429(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_JOIN_PER_MINUTE", "1")
    get_settings.cache_clear()
    reset_rate_limits()
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    first = other_client()
    ok = first.post(
        "/api/join-requests",
        json={"code": code, "display_name": "الأول"},
        headers=csrf_headers(first),
    )
    second = other_client()
    limited = second.post(
        "/api/join-requests",
        json={"code": code, "display_name": "الثاني"},
        headers=csrf_headers(second),
    )
    assert ok.status_code == 200
    assert limited.status_code == 429
    get_settings.cache_clear()
    reset_rate_limits()


def test_member_cannot_connect_websocket_after_room_closed(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = other_client()
    join = guest.post(
        "/api/join-requests",
        json={"code": created["invitations"][0]["code"], "display_name": "عضو"},
        headers=csrf_headers(guest),
    ).json()
    client.post(
        f"/api/join-requests/{join['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    client.post(f"/api/rooms/{room_id}/close", headers=csrf_headers(client))
    from starlette.websockets import WebSocketDisconnect
    import pytest

    with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


def test_docs_hidden_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://securechat.example")
    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as prod:
        assert prod.get("/api/docs").status_code == 404
        assert prod.get("/api/openapi.json").status_code == 404
        assert prod.get("/api/health").status_code == 200
    get_settings.cache_clear()
