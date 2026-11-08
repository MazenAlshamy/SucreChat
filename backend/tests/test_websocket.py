import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.conftest import create_room, csrf_headers


def test_owner_receives_join_request_immediately(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    code = created["invitations"][0]["code"]
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        connected = owner_ws.receive_json()
        assert connected["type"] == "connected"
        guest = TestClient(client.app)
        response = guest.post(
            "/api/join-requests",
            json={"code": code, "display_name": "سارة"},
            headers=csrf_headers(guest),
        )
        assert response.status_code == 200
        event = owner_ws.receive_json()
        assert event["type"] == "join_request"
        assert event["request"]["display_name"] == "سارة"
        assert event["request"]["status"] == "pending"


def test_request_status_updates_after_decision(client: TestClient) -> None:
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    guest = TestClient(client.app)
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "خالد"},
        headers=csrf_headers(guest),
    ).json()
    with guest.websocket_connect(f"/api/ws/join-requests/{request_payload['id']}") as guest_ws:
        assert guest_ws.receive_json()["type"] == "connected"
        decision = client.post(
            f"/api/join-requests/{request_payload['id']}/decision",
            json={"decision": "rejected"},
            headers=csrf_headers(client),
        )
        assert decision.status_code == 200
        event = guest_ws.receive_json()
        assert event["type"] == "request_updated"
        assert event["request"]["status"] == "rejected"


def test_members_update_on_approval_and_presence_on_leave(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    code = created["invitations"][0]["code"]
    guest = TestClient(client.app)
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "ليان"},
        headers=csrf_headers(guest),
    ).json()
    client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner_ws.receive_json()
        with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as guest_ws:
            guest_connected = guest_ws.receive_json()
            assert guest_connected["type"] == "connected"
            join_event = owner_ws.receive_json()
            assert join_event["type"] == "presence"
            assert join_event["action"] == "join"
            assert any(item["display_name"] == "ليان" for item in join_event["online_users"])
        leave_event = owner_ws.receive_json()
        assert leave_event["type"] == "presence"
        assert leave_event["action"] == "leave"


def test_unapproved_user_cannot_connect_to_room(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = TestClient(client.app)
    guest.post("/api/session", json={"display_name": "زائر"}, headers=csrf_headers(guest))
    with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


def test_member_cannot_connect_to_foreign_room(client: TestClient) -> None:
    first = create_room(client, name="غرفة أولى").json()
    second_owner = TestClient(client.app)
    second = create_room(second_owner, name="غرفة ثانية", display_name="مالك آخر").json()
    guest = TestClient(client.app)
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
    with guest.websocket_connect(f"/api/ws/rooms/{second['room']['id']}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


def test_unapproved_user_cannot_connect_to_request_socket(client: TestClient) -> None:
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    guest = TestClient(client.app)
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "سارة"},
        headers=csrf_headers(guest),
    ).json()
    stranger = TestClient(client.app)
    stranger.post("/api/session", json={"display_name": "غريب"}, headers=csrf_headers(stranger))
    with stranger.websocket_connect(f"/api/ws/join-requests/{request_payload['id']}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


def test_member_socket_closes_when_owner_closes_room(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    code = created["invitations"][0]["code"]
    guest = TestClient(client.app)
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "ليان"},
        headers=csrf_headers(guest),
    ).json()
    client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as guest_ws:
        guest_ws.receive_json()
        client.post(f"/api/rooms/{room_id}/close", headers=csrf_headers(client))
        with pytest.raises(WebSocketDisconnect) as exc:
            while True:
                guest_ws.receive_json()
        assert exc.value.code == 1008


def test_admin_events_from_socket_are_rejected(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner_ws.receive_json()
        owner_ws.send_json({"type": "decision", "decision": "approved"})
        error = owner_ws.receive_json()
        assert error["type"] == "error"


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


def test_media_signal_is_forwarded_to_other_member(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    code = created["invitations"][0]["code"]
    guest = TestClient(client.app)
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "ليان"},
        headers=csrf_headers(guest),
    ).json()
    client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
            owner_connected = owner_ws.receive_json()
            with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as guest_ws:
                guest_ws.receive_json()
                owner_ws.send_json({"type": "signal", "action": "join-media"})
                owner_peers = _drain_until(owner_ws, lambda item: item.get("action") == "media-peers")
                assert owner_peers["action"] == "media-peers"
                event = _drain_until(guest_ws, lambda item: item.get("action") == "join-media")
                assert event["type"] == "signal"
                assert event["from_user"]
                guest_ws.send_json({
                    "type": "signal",
                    "action": "offer",
                    "to_user": owner_connected["user_id"],
                    "data": {"type": "offer", "sdp": "v=0"},
                })
                targeted = _drain_until(owner_ws, lambda item: item.get("action") == "offer")
                assert targeted["type"] == "signal"
                assert targeted["to_user"] == owner_connected["user_id"]


def _drain_until(ws, predicate, limit: int = 12) -> dict:
    for _ in range(limit):
        payload = ws.receive_json()
        if predicate(payload):
            return payload
    raise AssertionError("expected websocket event was not received")


def test_late_joiner_receives_existing_media_peers(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created)
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner_connected = owner_ws.receive_json()
        owner_ws.send_json({"type": "signal", "action": "join-media"})
        owner_peers = _drain_until(owner_ws, lambda item: item.get("action") == "media-peers")
        assert owner_peers["peers"] == []
        with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as guest_ws:
            guest_ws.receive_json()
            _drain_until(owner_ws, lambda item: item.get("type") == "presence")
            guest_ws.send_json({"type": "signal", "action": "join-media"})
            guest_peers = _drain_until(guest_ws, lambda item: item.get("action") == "media-peers")
            assert any(item["user_id"] == owner_connected["user_id"] for item in guest_peers["peers"])
            join_event = _drain_until(owner_ws, lambda item: item.get("action") == "join-media")
            assert join_event["from_user"]


def test_media_leave_removes_peer_from_late_join_snapshot(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created, "خالد")
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner_ws.receive_json()
        owner_ws.send_json({"type": "signal", "action": "join-media"})
        _drain_until(owner_ws, lambda item: item.get("action") == "media-peers")
        with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as guest_ws:
            guest_ws.receive_json()
            owner_ws.send_json({"type": "signal", "action": "leave-media"})
            _drain_until(guest_ws, lambda item: item.get("action") == "leave-media")
            guest_ws.send_json({"type": "signal", "action": "join-media"})
            guest_peers = _drain_until(guest_ws, lambda item: item.get("action") == "media-peers")
            assert guest_peers["peers"] == []


def test_media_signal_rejected_when_room_closed(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    client.post(f"/api/rooms/{room_id}/close", headers=csrf_headers(client))
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        connected = owner_ws.receive_json()
        assert connected["type"] == "connected"
        owner_ws.send_json({"type": "signal", "action": "join-media"})
        error = owner_ws.receive_json()
        assert error["type"] == "error"


def test_unapproved_user_cannot_send_media_signal(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = TestClient(client.app)
    guest.post("/api/session", json={"display_name": "زائر"}, headers=csrf_headers(guest))
    with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


def test_websocket_reconnects_after_disconnect(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as first:
        first.receive_json()
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as second:
        payload = second.receive_json()
        assert payload["type"] == "connected"
        assert payload["room"]["id"] == room_id
