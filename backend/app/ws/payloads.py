from datetime import datetime

from app.models import Invitation, JoinRequest, Room, RoomMember
from app.ws.hub import hub


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def member_payload(member: RoomMember) -> dict:
    channel = f"room:{member.room_id}"
    return {
        "id": member.id,
        "user_id": member.user_id,
        "display_name": member.display_name,
        "role": member.role,
        "joined_at": _iso(member.joined_at),
        "online": hub.is_online(channel, member.user_id),
    }


def join_request_payload(item: JoinRequest, room_name: str | None = None) -> dict:
    return {
        "id": item.id,
        "room_id": item.room_id,
        "display_name": item.display_name,
        "status": item.status,
        "created_at": _iso(item.created_at),
        "decided_at": _iso(item.decided_at),
        "room_name": room_name,
    }


def room_payload(room: Room, member_count: int, pending_requests: int, is_owner: bool) -> dict:
    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
        "status": room.status,
        "max_participants": room.max_participants,
        "owner_id": room.owner_id,
        "created_at": _iso(room.created_at),
        "member_count": member_count,
        "pending_requests": pending_requests,
        "is_owner": is_owner,
    }


def invitation_payload(invitation: Invitation) -> dict:
    return {
        "id": invitation.id,
        "code_prefix": invitation.code_prefix,
        "status": invitation.status,
        "max_uses": invitation.max_uses,
        "use_count": invitation.use_count,
        "expires_at": _iso(invitation.expires_at),
        "created_at": _iso(invitation.created_at),
    }


def event(event_type: str, **payload) -> dict:
    return {"type": event_type, **payload}
