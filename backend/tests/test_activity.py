import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.conftest import create_room, csrf_headers, other_client


def _approve_guest(client: TestClient, created: dict, display_name: str = "ليان"):
    guest = TestClient(client.app)
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": created["invitations"][0]["code"], "display_name": display_name},
        headers=csrf_headers(guest),
    ).json()
    client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    return guest


def test_chat_requires_membership(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    stranger = other_client()
    stranger.post("/api/session", json={"display_name": "غريب"}, headers=csrf_headers(stranger))
    denied = stranger.get(f"/api/rooms/{room_id}/messages")
    assert denied.status_code in {401, 403}
    post = stranger.post(
        f"/api/rooms/{room_id}/messages",
        json={"body": "مرحبا"},
        headers=csrf_headers(stranger),
    )
    assert post.status_code in {401, 403}


def test_empty_chat_message_rejected(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    response = client.post(
        f"/api/rooms/{room_id}/messages",
        json={"body": "   "},
        headers=csrf_headers(client),
    )
    assert response.status_code == 400


def test_member_can_send_and_persist_chat(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created)
    sent = guest.post(
        f"/api/rooms/{room_id}/messages",
        json={"body": "مرحبا بالجميع"},
        headers=csrf_headers(guest),
    )
    assert sent.status_code == 200
    payload = sent.json()
    assert payload["body"] == "مرحبا بالجميع"
    history = client.get(f"/api/rooms/{room_id}/messages")
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert any(item["body"] == "مرحبا بالجميع" for item in messages)
    assert history.json()["unread_count"] >= 1


def test_two_members_exchange_chat_and_unread_state(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created, "سارة")
    first = client.post(
        f"/api/rooms/{room_id}/messages",
        json={"body": "من المالك"},
        headers=csrf_headers(client),
    )
    assert first.status_code == 200
    guest_inbox = guest.get(f"/api/rooms/{room_id}/messages")
    assert guest_inbox.status_code == 200
    assert guest_inbox.json()["unread_count"] >= 1
    assert any(item["body"] == "من المالك" for item in guest_inbox.json()["messages"])
    reply = guest.post(
        f"/api/rooms/{room_id}/messages",
        json={"body": "رد الضيف"},
        headers=csrf_headers(guest),
    )
    assert reply.status_code == 200
    owner_inbox = client.get(f"/api/rooms/{room_id}/messages")
    bodies = [item["body"] for item in owner_inbox.json()["messages"]]
    assert bodies == ["من المالك", "رد الضيف"]
    assert owner_inbox.json()["unread_count"] >= 1
    marked = guest.post(f"/api/rooms/{room_id}/messages/read", headers=csrf_headers(guest))
    assert marked.status_code == 200
    after_read = guest.get(f"/api/rooms/{room_id}/messages")
    assert after_read.json()["unread_count"] == 0


def test_chat_history_survives_socket_reconnect(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created, "ليان")
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner_ws.receive_json()
        guest.post(
            f"/api/rooms/{room_id}/messages",
            json={"body": "قبل إعادة الاتصال"},
            headers=csrf_headers(guest),
        )
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as again:
        again.receive_json()
    history = client.get(f"/api/rooms/{room_id}/messages")
    bodies = [item["body"] for item in history.json()["messages"]]
    assert bodies.count("قبل إعادة الاتصال") == 1


def test_sequential_chat_keeps_order(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created, "خالد")
    for index in range(3):
        response = client.post(
            f"/api/rooms/{room_id}/messages",
            json={"body": f"رسالة {index + 1}"},
            headers=csrf_headers(client),
        )
        assert response.status_code == 200
    history = guest.get(f"/api/rooms/{room_id}/messages")
    bodies = [item["body"] for item in history.json()["messages"] if item["body"].startswith("رسالة")]
    assert bodies[-3:] == ["رسالة 1", "رسالة 2", "رسالة 3"]


def test_chat_over_websocket_reaches_other_member(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created, "سارة")
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner_ws.receive_json()
        with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as guest_ws:
            guest_ws.receive_json()
            owner_ws.receive_json()
            guest_ws.send_json({"type": "chat", "body": "رسالة فورية"})
            ack = guest_ws.receive_json()
            assert ack["type"] in {"chat_ack", "chat_message"}
            event = owner_ws.receive_json()
            while event.get("type") not in {"chat_message", "chat_ack"}:
                event = owner_ws.receive_json()
            body = event.get("message", {}).get("body") or event.get("body")
            assert body == "رسالة فورية"


def test_join_request_creates_owner_notification(client: TestClient) -> None:
    created = create_room(client).json()
    guest = other_client()
    guest.post(
        "/api/join-requests",
        json={"code": created["invitations"][0]["code"], "display_name": "خالد"},
        headers=csrf_headers(guest),
    )
    inbox = client.get("/api/notifications")
    assert inbox.status_code == 200
    items = inbox.json()["items"]
    assert any(item["type"] == "join_request" for item in items)
    unread = inbox.json()["unread_count"]
    assert unread >= 1
    first = next(item for item in items if item["type"] == "join_request")
    marked = client.post(f"/api/notifications/{first['id']}/read", headers=csrf_headers(client))
    assert marked.status_code == 200
    assert marked.json()["read"] is True


def test_approval_notifies_guest_and_inbox_summary(client: TestClient) -> None:
    created = create_room(client).json()
    guest = other_client()
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": created["invitations"][0]["code"], "display_name": "ليان"},
        headers=csrf_headers(guest),
    ).json()
    client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    notes = guest.get("/api/notifications").json()["items"]
    assert any(item["type"] == "join_approved" for item in notes)
    summary = client.get("/api/inbox/summary")
    assert summary.status_code == 200
    assert "notifications" in summary.json()
    assert "join_requests" in summary.json()


def test_meeting_timer_starts_on_first_meeting_access(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    first = client.get(f"/api/rooms/{room_id}/meeting")
    assert first.status_code == 200
    payload = first.json()
    assert payload["meeting_started_at"]
    assert payload["meeting_running"] is True
    assert payload["elapsed_seconds"] >= 0
    second = client.get(f"/api/rooms/{room_id}/meeting")
    assert second.json()["meeting_started_at"] == payload["meeting_started_at"]


def test_closing_room_stops_meeting_timer(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    client.get(f"/api/rooms/{room_id}/meeting")
    client.post(f"/api/rooms/{room_id}/close", headers=csrf_headers(client))
    meeting = client.get(f"/api/rooms/{room_id}/meeting")
    assert meeting.status_code == 200
    assert meeting.json()["meeting_ended_at"]
    assert meeting.json()["meeting_running"] is False


def test_inbox_websocket_requires_session(client: TestClient) -> None:
    stranger = other_client()
    with stranger.websocket_connect("/api/ws/inbox") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


def test_inbox_websocket_connects_for_session_user(client: TestClient) -> None:
    created = create_room(client).json()
    assert created["room"]["id"]
    with client.websocket_connect("/api/ws/inbox") as ws:
        payload = ws.receive_json()
        assert payload["type"] == "connected"
        assert payload["user_id"]
