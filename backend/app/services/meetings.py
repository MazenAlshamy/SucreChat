from sqlalchemy.orm import Session

from app.models import Room, User
from app.security import utcnow
from app.services import rooms as room_service


def ensure_meeting_started(db: Session, room: Room) -> Room:
    if room.meeting_started_at is None:
        room.meeting_started_at = utcnow()
        room.meeting_ended_at = None
        db.flush()
    return room


def meeting_payload(room: Room) -> dict:
    started = room.meeting_started_at
    ended = room.meeting_ended_at
    now = utcnow()
    elapsed = 0
    if started:
        end_point = ended or now
        elapsed = max(0, int((end_point - started).total_seconds()))
    return {
        "meeting_started_at": started.isoformat() if started else None,
        "meeting_ended_at": ended.isoformat() if ended else None,
        "elapsed_seconds": elapsed,
        "running": bool(started and ended is None and room.status == "active"),
    }


def open_meeting(db: Session, room: Room, user: User) -> tuple:
    membership = room_service.require_room_access(db, room, user)
    if room.status == "active":
        ensure_meeting_started(db, room)
    return membership, meeting_payload(room)
