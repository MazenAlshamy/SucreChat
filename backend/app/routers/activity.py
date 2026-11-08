from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.errors import not_found
from app.models import User
from app.rate_limit import check_rate_limit
from app.schemas.activity import (
    ChatHistoryView,
    ChatMessageCreate,
    ChatMessageView,
    NotificationListView,
    NotificationView,
    UnreadSummary,
)
from app.services import chat as chat_service
from app.services import notifications as notification_service
from app.services import rooms as room_service

router = APIRouter(prefix="/api", tags=["activity"])


def _client_key(request: Request, suffix: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{suffix}"


def _message_view(message, user_id: str) -> ChatMessageView:
    return ChatMessageView(**chat_service.message_payload(message, user_id))


def _notification_view(item, room_name: str | None) -> NotificationView:
    return NotificationView(**notification_service.notification_payload(item, room_name))


@router.get("/rooms/{room_id}/messages", response_model=ChatHistoryView)
def list_room_messages(
    room_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatHistoryView:
    room = room_service.get_room_or_404(db, room_id)
    messages = chat_service.list_messages(db, room, user)
    unread = chat_service.unread_count(db, room, user)
    return ChatHistoryView(
        messages=[_message_view(item, user.id) for item in messages],
        unread_count=unread,
    )


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageView)
def post_room_message(
    room_id: str,
    payload: ChatMessageCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessageView:
    settings = get_settings()
    check_rate_limit(_client_key(request, f"chat:{room_id}"), settings.rate_limit_chat_per_minute)
    room = room_service.get_room_or_404(db, room_id)
    message = chat_service.create_message(db, room, user, payload.body)
    return _message_view(message, user.id)


@router.post("/rooms/{room_id}/messages/read")
def mark_room_messages_read(
    room_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    room = room_service.get_room_or_404(db, room_id)
    room_service.require_room_access(db, room, user)
    chat_service.mark_read(db, room, user)
    return {"ok": True}


@router.get("/notifications", response_model=NotificationListView)
def list_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListView:
    items = notification_service.list_notifications(db, user)
    return NotificationListView(
        items=[
            _notification_view(item, notification_service.room_name_for(db, item.room_id))
            for item in items
        ],
        unread_count=notification_service.unread_count(db, user),
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationView)
def read_notification(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationView:
    item = notification_service.mark_read(db, user, notification_id)
    if item is None:
        raise not_found("الإشعار غير موجود")
    return _notification_view(item, notification_service.room_name_for(db, item.room_id))


@router.post("/notifications/read-all")
def read_all_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    updated = notification_service.mark_all_read(db, user)
    return {"ok": True, "updated": updated}


@router.get("/inbox/summary", response_model=UnreadSummary)
def inbox_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadSummary:
    pending = 0
    for room in room_service.list_owned_rooms(db, user):
        pending += sum(1 for item in room.join_requests if item.status == "pending")
    return UnreadSummary(
        notifications=notification_service.unread_count(db, user),
        messages=chat_service.total_unread_for_user(db, user),
        join_requests=pending,
    )
