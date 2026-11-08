from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Notification, Room, User
from app.security import new_id, utcnow
from app.ws.publish import publish_user_event


def create_notification(
    db: Session,
    *,
    user_id: str,
    ntype: str,
    title: str,
    body: str,
    link: str,
    room_id: str | None = None,
    join_request_id: str | None = None,
    message_id: str | None = None,
) -> Notification:
    item = Notification(
        id=new_id(),
        user_id=user_id,
        type=ntype,
        title=title,
        body=body,
        room_id=room_id,
        join_request_id=join_request_id,
        message_id=message_id,
        link=link,
        created_at=utcnow(),
    )
    db.add(item)
    db.flush()
    return item


def notification_payload(item: Notification, room_name: str | None = None) -> dict:
    return {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "body": item.body,
        "room_id": item.room_id,
        "room_name": room_name,
        "join_request_id": item.join_request_id,
        "link": item.link,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "read": item.read_at is not None,
    }


def publish_notification(item: Notification, room_name: str | None = None) -> None:
    publish_user_event(
        item.user_id,
        {
            "type": "notification",
            "notification": notification_payload(item, room_name),
        },
    )


def notify_users(
    db: Session,
    user_ids: list[str],
    *,
    ntype: str,
    title: str,
    body: str,
    link: str,
    room: Room | None = None,
    join_request_id: str | None = None,
    message_id: str | None = None,
    exclude_user: str | None = None,
) -> list[Notification]:
    created: list[Notification] = []
    room_name = room.name if room else None
    room_id = room.id if room else None
    seen: set[str] = set()
    for user_id in user_ids:
        if not user_id or user_id == exclude_user or user_id in seen:
            continue
        seen.add(user_id)
        item = create_notification(
            db,
            user_id=user_id,
            ntype=ntype,
            title=title,
            body=body,
            link=link,
            room_id=room_id,
            join_request_id=join_request_id,
            message_id=message_id,
        )
        created.append(item)
        publish_notification(item, room_name)
    return created


def list_notifications(db: Session, user: User, limit: int = 50) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )


def unread_count(db: Session, user: User) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        )
        or 0
    )


def mark_read(db: Session, user: User, notification_id: str) -> Notification | None:
    item = db.get(Notification, notification_id)
    if item is None or item.user_id != user.id:
        return None
    if item.read_at is None:
        item.read_at = utcnow()
        db.flush()
    return item


def mark_all_read(db: Session, user: User) -> int:
    now = utcnow()
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read_at.is_(None))
        .update({"read_at": now}, synchronize_session=False)
    )
    db.flush()
    return int(updated or 0)


def room_name_for(db: Session, room_id: str | None) -> str | None:
    if not room_id:
        return None
    room = db.get(Room, room_id)
    return room.name if room else None
