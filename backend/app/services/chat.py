from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import bad_request, forbidden, too_many
from app.models import Room, RoomMessage, RoomMessageRead, User
from app.security import new_id, utcnow
from app.services import notifications as notification_service
from app.services import rooms as room_service
from app.ws.publish import publish_room_chat


def validate_message_body(body: str) -> str:
    settings = get_settings()
    cleaned = (body or "").strip()
    if not cleaned:
        raise bad_request("لا يمكن إرسال رسالة فارغة")
    if len(cleaned) > settings.chat_message_max_length:
        raise bad_request("الرسالة أطول من الحد المسموح")
    return cleaned


def _recent_count(db: Session, room_id: str, user_id: str) -> int:
    window_start = utcnow() - timedelta(seconds=60)
    return (
        db.scalar(
            select(func.count())
            .select_from(RoomMessage)
            .where(
                RoomMessage.room_id == room_id,
                RoomMessage.user_id == user_id,
                RoomMessage.created_at >= window_start,
            )
        )
        or 0
    )


def list_messages(db: Session, room: Room, user: User, limit: int = 80) -> list[RoomMessage]:
    room_service.require_room_access(db, room, user)
    items = (
        db.query(RoomMessage)
        .filter(RoomMessage.room_id == room.id)
        .order_by(RoomMessage.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    items.reverse()
    return items


def unread_count(db: Session, room: Room, user: User) -> int:
    cursor = (
        db.query(RoomMessageRead)
        .filter(RoomMessageRead.room_id == room.id, RoomMessageRead.user_id == user.id)
        .one_or_none()
    )
    query = db.query(func.count()).select_from(RoomMessage).filter(
        RoomMessage.room_id == room.id,
        RoomMessage.user_id != user.id,
    )
    if cursor is not None:
        query = query.filter(RoomMessage.created_at > cursor.last_read_at)
    return query.scalar() or 0


def mark_read(db: Session, room: Room, user: User) -> None:
    now = utcnow()
    cursor = (
        db.query(RoomMessageRead)
        .filter(RoomMessageRead.room_id == room.id, RoomMessageRead.user_id == user.id)
        .one_or_none()
    )
    if cursor is None:
        db.add(
            RoomMessageRead(
                id=new_id(),
                room_id=room.id,
                user_id=user.id,
                last_read_at=now,
            )
        )
    else:
        cursor.last_read_at = now
    db.flush()


def create_message(db: Session, room: Room, user: User, body: str) -> RoomMessage:
    membership = room_service.require_room_access(db, room, user)
    if room.status != "active":
        raise forbidden("الغرفة مغلقة ولا يمكن إرسال رسائل")
    cleaned = validate_message_body(body)
    settings = get_settings()
    if _recent_count(db, room.id, user.id) >= settings.rate_limit_chat_per_minute:
        raise too_many("تم تجاوز حد إرسال الرسائل، حاول بعد قليل")
    message = RoomMessage(
        id=new_id(),
        room_id=room.id,
        user_id=user.id,
        display_name=membership.display_name or user.display_name,
        body=cleaned,
        created_at=utcnow(),
    )
    db.add(message)
    mark_read(db, room, user)
    db.flush()
    members = room_service.list_members(db, room)
    notification_service.notify_users(
        db,
        [member.user_id for member in members],
        ntype="chat_message",
        title="رسالة جديدة",
        body=f"{message.display_name}: {cleaned[:80]}",
        link=f"/rooms/{room.id}/meeting",
        room=room,
        message_id=message.id,
        exclude_user=user.id,
    )
    publish_room_chat(room.id, message_payload(message))
    return message


def message_payload(message: RoomMessage, current_user_id: str | None = None) -> dict:
    return {
        "id": message.id,
        "room_id": message.room_id,
        "user_id": message.user_id,
        "display_name": message.display_name,
        "body": message.body,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "mine": bool(current_user_id and message.user_id == current_user_id),
    }


def total_unread_for_user(db: Session, user: User) -> int:
    rooms = room_service.list_member_rooms(db, user)
    return sum(unread_count(db, room, user) for room in rooms)
