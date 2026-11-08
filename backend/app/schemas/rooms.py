from datetime import datetime

from pydantic import BaseModel, Field


class CreateRoomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    max_participants: int | None = None
    display_name: str = Field(min_length=2, max_length=40)
    allow_guest_requests: bool = True
    invite_max_uses: int | None = None
    invite_expires_in_hours: int | None = 24


class CreateInvitationRequest(BaseModel):
    max_uses: int | None = None
    expires_in_hours: int | None = None


class JoinRequestPayload(BaseModel):
    code: str = Field(min_length=8, max_length=80)
    display_name: str = Field(min_length=2, max_length=40)


class DecisionPayload(BaseModel):
    decision: str


class RoomSummary(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    max_participants: int
    owner_id: str
    created_at: datetime
    member_count: int
    pending_requests: int = 0
    is_owner: bool = False


class InvitationView(BaseModel):
    id: str
    code_prefix: str
    status: str
    max_uses: int | None
    use_count: int
    expires_at: datetime | None
    created_at: datetime
    invite_url: str | None = None
    code: str | None = None


class JoinRequestView(BaseModel):
    id: str
    room_id: str
    display_name: str
    status: str
    created_at: datetime
    decided_at: datetime | None
    room_name: str | None = None


class MemberView(BaseModel):
    id: str
    user_id: str
    display_name: str
    role: str
    joined_at: datetime


class RoomDetail(BaseModel):
    room: RoomSummary
    invitations: list[InvitationView] = []
    join_requests: list[JoinRequestView] = []
    members: list[MemberView] = []


class InvitePreview(BaseModel):
    valid: bool
    reason: str | None = None
    room_name: str | None = None
    room_status: str | None = None
    max_participants: int | None = None
    description: str | None = None
    expires_at: datetime | None = None


class MeetingView(BaseModel):
    room: RoomSummary
    members: list[MemberView]
    role: str
    user_id: str
    media_enabled: bool = False
    media_provider: str = "none"
    media_reason: str | None = None
    meeting_started_at: str | None = None
    meeting_ended_at: str | None = None
    elapsed_seconds: int = 0
    meeting_running: bool = False
    unread_messages: int = 0


class LiveKitTokenView(BaseModel):
    url: str
    token: str
    room_name: str
    identity: str
    expires_in: int
