from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.database import get_session_factory
from app.models import Invitation, Room
from tests.conftest import create_room, csrf_headers, other_client


def _expire_invitation(invitation_id: str) -> None:
    db = get_session_factory()()
    invitation = db.get(Invitation, invitation_id)
    invitation.expires_at = datetime.utcnow() - timedelta(hours=1)
    db.commit()
    db.close()


def _close_room(room_id: str) -> None:
    db = get_session_factory()()
    room = db.get(Room, room_id)
    room.status = "closed"
    db.commit()
    db.close()


def test_create_room_with_valid_data(client: TestClient) -> None:
    response = create_room(client)
    assert response.status_code == 200
    payload = response.json()
    assert payload["room"]["name"] == "غرفة الاختبار"
    assert payload["room"]["status"] == "active"
    assert payload["room"]["is_owner"] is True
    assert payload["room"]["member_count"] == 1
    assert payload["invitations"][0]["code"]


def test_reject_invalid_room_payload(client: TestClient) -> None:
    response = client.post(
        "/api/rooms",
        json={"name": " ", "display_name": "مالك", "max_participants": 1},
        headers=csrf_headers(client),
    )
    assert response.status_code == 400


def test_create_valid_invitation(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    response = client.post(
        f"/api/rooms/{room_id}/invitations",
        json={"max_uses": 3, "expires_in_hours": 2},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["code"]
    assert response.json()["max_uses"] == 3


def test_reject_expired_invitation(client: TestClient) -> None:
    created = create_room(client).json()
    invitation = created["invitations"][0]
    _expire_invitation(invitation["id"])
    guest = other_client()
    preview = guest.get(f"/api/invites/{invitation['code']}")
    assert preview.status_code == 200
    assert preview.json()["valid"] is False
    join = guest.post(
        "/api/join-requests",
        json={"code": invitation["code"], "display_name": "ضيف"},
        headers=csrf_headers(guest),
    )
    assert join.status_code == 403


def test_reject_revoked_invitation(client: TestClient) -> None:
    created = create_room(client).json()
    invitation = created["invitations"][0]
    revoke = client.post(
        f"/api/invitations/{invitation['id']}/revoke",
        headers=csrf_headers(client),
    )
    assert revoke.status_code == 200
    guest = other_client()
    join = guest.post(
        "/api/join-requests",
        json={"code": invitation["code"], "display_name": "ضيف"},
        headers=csrf_headers(guest),
    )
    assert join.status_code == 403


def test_reject_invitation_use_limit(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    invitation = client.post(
        f"/api/rooms/{room_id}/invitations",
        json={"max_uses": 1, "expires_in_hours": 12},
        headers=csrf_headers(client),
    ).json()
    guest = other_client()
    first = guest.post(
        "/api/join-requests",
        json={"code": invitation["code"], "display_name": "ضيف واحد"},
        headers=csrf_headers(guest),
    )
    assert first.status_code == 200
    another = other_client()
    second = another.post(
        "/api/join-requests",
        json={"code": invitation["code"], "display_name": "ضيف اثنان"},
        headers=csrf_headers(another),
    )
    assert second.status_code == 403


def test_submit_valid_join_request_stays_pending(client: TestClient) -> None:
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    guest = other_client()
    response = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "سارة"},
        headers=csrf_headers(guest),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    meeting = guest.get(f"/api/rooms/{payload['room_id']}/meeting")
    assert meeting.status_code == 403


def test_invalid_invitation_does_not_create_request(client: TestClient) -> None:
    guest = other_client()
    response = guest.post(
        "/api/join-requests",
        json={"code": "not-a-real-invite-code", "display_name": "سارة"},
        headers=csrf_headers(guest),
    )
    assert response.status_code == 404


def test_owner_can_approve_pending_request(client: TestClient) -> None:
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    guest = other_client()
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "سارة"},
        headers=csrf_headers(guest),
    ).json()
    decision = client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"
    meeting = guest.get(f"/api/rooms/{request_payload['room_id']}/meeting")
    assert meeting.status_code == 200
    payload = meeting.json()
    assert payload["media_enabled"] is True
    assert payload["media_provider"] == "webrtc"
    assert payload["user_id"]


def test_owner_can_reject_pending_request(client: TestClient) -> None:
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    guest = other_client()
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "خالد"},
        headers=csrf_headers(guest),
    ).json()
    decision = client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "rejected"},
        headers=csrf_headers(client),
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "rejected"
    meeting = guest.get(f"/api/rooms/{request_payload['room_id']}/meeting")
    assert meeting.status_code == 403


def test_regular_user_cannot_approve_others(client: TestClient) -> None:
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    guest = other_client()
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "سارة"},
        headers=csrf_headers(guest),
    ).json()
    decision = guest.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(guest),
    )
    assert decision.status_code == 403


def test_regular_user_cannot_revoke_invites(client: TestClient) -> None:
    created = create_room(client).json()
    invitation_id = created["invitations"][0]["id"]
    guest = other_client()
    guest.post(
        "/api/session",
        json={"display_name": "مستخدم عادي"},
        headers=csrf_headers(guest),
    )
    response = guest.post(
        f"/api/invitations/{invitation_id}/revoke",
        headers=csrf_headers(guest),
    )
    assert response.status_code == 403


def test_user_cannot_manage_foreign_room(client: TestClient) -> None:
    created = create_room(client).json()
    room_id = created["room"]["id"]
    stranger = other_client()
    stranger.post("/api/session", json={"display_name": "غريب"}, headers=csrf_headers(stranger))
    response = stranger.post(f"/api/rooms/{room_id}/close", headers=csrf_headers(stranger))
    assert response.status_code == 403


def test_member_cannot_access_another_room(client: TestClient) -> None:
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
    allowed = guest.get(f"/api/rooms/{first['room']['id']}/meeting")
    denied = guest.get(f"/api/rooms/{second['room']['id']}/meeting")
    assert allowed.status_code == 200
    assert denied.status_code == 403


def test_duplicate_join_requests_reuse_pending(client: TestClient) -> None:
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    guest = other_client()
    first = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "سارة"},
        headers=csrf_headers(guest),
    ).json()
    second = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "سارة المحدث"},
        headers=csrf_headers(guest),
    ).json()
    assert first["id"] == second["id"]
    assert second["status"] == "pending"
    assert second["display_name"] == "سارة المحدث"


def test_cannot_decide_non_pending_request(client: TestClient) -> None:
    created = create_room(client).json()
    code = created["invitations"][0]["code"]
    guest = other_client()
    request_payload = guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "سارة"},
        headers=csrf_headers(guest),
    ).json()
    first = client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "rejected"},
        headers=csrf_headers(client),
    )
    second = client.post(
        f"/api/join-requests/{request_payload['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    assert first.status_code == 200
    assert second.status_code == 409


def test_cannot_approve_when_room_full_or_closed(client: TestClient) -> None:
    created = create_room(client, max_participants=2).json()
    code = created["invitations"][0]["code"]
    first_guest = other_client()
    first_request = first_guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "الأول"},
        headers=csrf_headers(first_guest),
    ).json()
    client.post(
        f"/api/join-requests/{first_request['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    second_guest = other_client()
    second_request = second_guest.post(
        "/api/join-requests",
        json={"code": code, "display_name": "الثاني"},
        headers=csrf_headers(second_guest),
    ).json()
    full = client.post(
        f"/api/join-requests/{second_request['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(client),
    )
    assert full.status_code == 409

    third_owner = other_client()
    closed_room = create_room(third_owner, name="مغلقة", display_name="مالك مغلق").json()
    closed_code = closed_room["invitations"][0]["code"]
    third_guest = other_client()
    pending = third_guest.post(
        "/api/join-requests",
        json={"code": closed_code, "display_name": "لاحق"},
        headers=csrf_headers(third_guest),
    ).json()
    _close_room(closed_room["room"]["id"])
    closed_decision = third_owner.post(
        f"/api/join-requests/{pending['id']}/decision",
        json={"decision": "approved"},
        headers=csrf_headers(third_owner),
    )
    assert closed_decision.status_code == 403
