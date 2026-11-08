from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class ChatMessageView(BaseModel):
    id: str
    room_id: str
    user_id: str
    display_name: str
    body: str
    created_at: datetime
    mine: bool = False


class ChatHistoryView(BaseModel):
    messages: list[ChatMessageView]
    unread_count: int = 0


class NotificationView(BaseModel):
    id: str
    type: str
    title: str
    body: str
    room_id: str | None = None
    room_name: str | None = None
    join_request_id: str | None = None
    link: str
    created_at: datetime
    read: bool = False


class NotificationListView(BaseModel):
    items: list[NotificationView]
    unread_count: int = 0


class UnreadSummary(BaseModel):
    notifications: int = 0
    messages: int = 0
    join_requests: int = 0
