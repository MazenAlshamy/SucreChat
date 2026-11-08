from fastapi.testclient import TestClient

from tests.conftest import create_room, csrf_headers
from tests.test_websocket import _approve_guest, _drain_until


def test_join_media_then_leave_updates_peer_snapshot(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created, "نورة")
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner = owner_ws.receive_json()
        owner_ws.send_json({"type": "signal", "action": "join-media"})
        _drain_until(owner_ws, lambda item: item.get("action") == "media-peers")
        with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as guest_ws:
            guest_ws.receive_json()
            guest_ws.send_json({"type": "signal", "action": "join-media"})
            peers = _drain_until(guest_ws, lambda item: item.get("action") == "media-peers")
            assert any(item["user_id"] == owner["user_id"] for item in peers["peers"])
            guest_ws.send_json(
                {
                    "type": "signal",
                    "action": "media-state",
                    "state": {"cameraOn": False, "micOn": True},
                }
            )
            state = _drain_until(owner_ws, lambda item: item.get("action") == "media-state")
            assert state["state"]["cameraOn"] is False
            assert state["state"]["micOn"] is True


def test_three_members_receive_mesh_peer_lists(client: TestClient) -> None:
    created = create_room(client, max_participants=5).json()
    room_id = created["room"]["id"]
    first = _approve_guest(client, created, "ليان")
    second = _approve_guest(client, created, "خالد")
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner = owner_ws.receive_json()
        owner_ws.send_json({"type": "signal", "action": "join-media"})
        _drain_until(owner_ws, lambda item: item.get("action") == "media-peers")
        with first.websocket_connect(f"/api/ws/rooms/{room_id}") as first_ws:
            first_ws.receive_json()
            first_ws.send_json({"type": "signal", "action": "join-media"})
            first_peers = _drain_until(first_ws, lambda item: item.get("action") == "media-peers")
            assert any(item["user_id"] == owner["user_id"] for item in first_peers["peers"])
            with second.websocket_connect(f"/api/ws/rooms/{room_id}") as second_ws:
                second_connected = second_ws.receive_json()
                second_ws.send_json({"type": "signal", "action": "join-media"})
                second_peers = _drain_until(second_ws, lambda item: item.get("action") == "media-peers")
                peer_ids = {item["user_id"] for item in second_peers["peers"]}
                assert owner["user_id"] in peer_ids
                assert len(peer_ids) >= 2
                second_ws.send_json(
                    {
                        "type": "signal",
                        "action": "offer",
                        "to_user": owner["user_id"],
                        "data": {"type": "offer", "sdp": "v=0"},
                    }
                )
                targeted = _drain_until(owner_ws, lambda item: item.get("action") == "offer")
                assert targeted["to_user"] == owner["user_id"]
                assert targeted["from_user"] == second_connected["user_id"]


def test_leave_media_notifies_remaining_members(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    guest = _approve_guest(client, created, "نورة")
    extra = _approve_guest(client, created, "ليان")
    with client.websocket_connect(f"/api/ws/rooms/{room_id}") as owner_ws:
        owner_ws.receive_json()
        owner_ws.send_json({"type": "signal", "action": "join-media"})
        _drain_until(owner_ws, lambda item: item.get("action") == "media-peers")
        with guest.websocket_connect(f"/api/ws/rooms/{room_id}") as guest_ws:
            guest_ws.receive_json()
            guest_ws.send_json({"type": "signal", "action": "join-media"})
            _drain_until(guest_ws, lambda item: item.get("action") == "media-peers")
            with extra.websocket_connect(f"/api/ws/rooms/{room_id}") as extra_ws:
                extra_ws.receive_json()
                extra_ws.send_json({"type": "signal", "action": "join-media"})
                _drain_until(extra_ws, lambda item: item.get("action") == "media-peers")
                guest_ws.send_json({"type": "signal", "action": "leave-media"})
                left = _drain_until(extra_ws, lambda item: item.get("action") == "leave-media")
                assert left["from_user"]
