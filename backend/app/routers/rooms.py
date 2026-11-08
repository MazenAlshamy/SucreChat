from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Invitation, JoinRequest, Room, RoomMember, User
from app.rate_limit import check_rate_limit
from app.config import get_settings
from app.schemas.rooms import (
    CreateInvitationRequest,
    CreateRoomRequest,
    DecisionPayload,
    InvitationView,
    InvitePreview,
    JoinRequestPayload,
    JoinRequestView,
    LiveKitTokenView,
    MeetingView,
    MemberView,
    RoomDetail,
    RoomSummary,
)
from app.services import chat as chat_service
from app.services import identity as identity_service
from app.services import livekit as livekit_service
from app.services import meetings as meeting_service
from app.services import notifications as notification_service
from app.services import rooms as room_service
from app.ws.publish import publish_join_request, publish_request_decision, publish_room_updated

router = APIRouter(prefix="/api", tags=["rooms"])


def _client_key(request: Request, suffix: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{suffix}"


def _room_summary(db: Session, room: Room, user: User | None = None) -> RoomSummary:
    pending = 0
    if user and room.owner_id == user.id:
        pending = sum(1 for item in room.join_requests if item.status == "pending")
    return RoomSummary(
        id=room.id,
        name=room.name,
        description=room.description,
        status=room.status,
        max_participants=room.max_participants,
        owner_id=room.owner_id,
        created_at=room.created_at,
        member_count=room_service.active_member_count(db, room.id),
        pending_requests=pending,
        is_owner=bool(user and room.owner_id == user.id),
    )


def _invitation_view(invitation: Invitation, code: str | None = None) -> InvitationView:
    return InvitationView(
        id=invitation.id,
        code_prefix=invitation.code_prefix,
        status=invitation.status,
        max_uses=invitation.max_uses,
        use_count=invitation.use_count,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        invite_url=f"/join/{code}" if code else None,
        code=code,
    )


def _join_view(item: JoinRequest, room_name: str | None = None) -> JoinRequestView:
    return JoinRequestView(
        id=item.id,
        room_id=item.room_id,
        display_name=item.display_name,
        status=item.status,
        created_at=item.created_at,
        decided_at=item.decided_at,
        room_name=room_name,
    )


def _member_view(member: RoomMember) -> MemberView:
    return MemberView(
        id=member.id,
        user_id=member.user_id,
        display_name=member.display_name,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.post("/rooms", response_model=RoomDetail)
def create_room(
    payload: CreateRoomRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> RoomDetail:
    settings = get_settings()
    check_rate_limit(_client_key(request, "room-create"), settings.rate_limit_room_create_per_minute)
    display_name = room_service.validate_display_name(payload.display_name)
    user = identity_service.ensure_session_user(db, request, response, display_name)
    room = room_service.create_room(
        db,
        user,
        payload.name,
        payload.description,
        payload.max_participants,
        payload.allow_guest_requests,
    )
    invitation, code = room_service.create_invitation(
        db,
        room,
        user,
        payload.invite_max_uses,
        payload.invite_expires_in_hours,
    )
    notification_service.notify_users(
        db,
        [user.id],
        ntype="room_created",
        title="أُنشئت الغرفة",
        body=f"غرفة {room.name} جاهزة. يمكنك بدء الاجتماع أو مشاركة الدعوة.",
        link=f"/rooms/{room.id}",
        room=room,
    )
    return RoomDetail(
        room=_room_summary(db, room, user),
        invitations=[_invitation_view(invitation, code)],
        join_requests=[],
        members=[_member_view(member) for member in room_service.list_members(db, room)],
    )


@router.get("/rooms", response_model=list[RoomSummary])
def list_my_rooms(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RoomSummary]:
    rooms = room_service.list_member_rooms(db, user)
    return [_room_summary(db, room, user) for room in rooms]


@router.get("/rooms/{room_id}", response_model=RoomDetail)
def get_room(
    room_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoomDetail:
    room = room_service.get_room_or_404(db, room_id)
    room_service.require_room_access(db, room, user)
    invitations = []
    requests = []
    if room_service.is_owner(room, user):
        invitations = [_invitation_view(item) for item in room_service.list_invitations(db, room, user)]
        requests = [
            _join_view(item) for item in room_service.list_join_requests(db, room, user)
        ]
    return RoomDetail(
        room=_room_summary(db, room, user),
        invitations=invitations,
        join_requests=requests,
        members=[_member_view(item) for item in room_service.list_members(db, room)],
    )


@router.post("/rooms/{room_id}/close", response_model=RoomSummary)
def close_room(
    room_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoomSummary:
    room = room_service.get_room_or_404(db, room_id)
    room = room_service.close_room(db, room, user)
    db.flush()
    publish_room_updated(db, room)
    return _room_summary(db, room, user)


@router.post("/rooms/{room_id}/invitations", response_model=InvitationView)
def create_invitation(
    room_id: str,
    payload: CreateInvitationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationView:
    room = room_service.get_room_or_404(db, room_id)
    invitation, code = room_service.create_invitation(
        db, room, user, payload.max_uses, payload.expires_in_hours
    )
    return _invitation_view(invitation, code)


@router.post("/invitations/{invitation_id}/revoke", response_model=InvitationView)
def revoke_invitation(
    invitation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationView:
    invitation = db.get(Invitation, invitation_id)
    if invitation is None:
        from app.errors import not_found

        raise not_found("الدعوة غير موجودة")
    invitation = room_service.revoke_invitation(db, invitation, user)
    return _invitation_view(invitation)


@router.get("/invites/{code}", response_model=InvitePreview)
def preview_invite(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
) -> InvitePreview:
    settings = get_settings()
    check_rate_limit(_client_key(request, "invite-lookup"), settings.rate_limit_invite_lookup_per_minute)
    invitation = room_service.get_invitation_by_code(db, code)
    if invitation is None:
        return InvitePreview(valid=False, reason="الدعوة غير صالحة")
    room = room_service.get_room_or_404(db, invitation.room_id)
    payload = room_service.public_invite_payload(invitation, room)
    return InvitePreview(**payload)


@router.post("/join-requests", response_model=JoinRequestView)
def submit_join_request(
    payload: JoinRequestPayload,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> JoinRequestView:
    settings = get_settings()
    check_rate_limit(_client_key(request, "join"), settings.rate_limit_join_per_minute)
    display_name = room_service.validate_display_name(payload.display_name)
    user = identity_service.ensure_session_user(db, request, response, display_name)
    item = room_service.submit_join_request(db, user, payload.code, display_name)
    room = room_service.get_room_or_404(db, item.room_id)
    db.flush()
    publish_join_request(db, item, room)
    return _join_view(item, room.name)


@router.get("/join-requests/{request_id}", response_model=JoinRequestView)
def read_join_request(
    request_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JoinRequestView:
    item = room_service.get_join_request_for_user(db, request_id, user)
    room = room_service.get_room_or_404(db, item.room_id)
    return _join_view(item, room.name)


@router.post("/join-requests/{request_id}/decision", response_model=JoinRequestView)
def decide_join_request(
    request_id: str,
    payload: DecisionPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JoinRequestView:
    item = room_service.decide_join_request(db, request_id, user, payload.decision)
    room = room_service.get_room_or_404(db, item.room_id)
    db.flush()
    publish_request_decision(db, item, room)
    return _join_view(item, room.name)


@router.get("/rooms/{room_id}/meeting", response_model=MeetingView)
def get_meeting(
    room_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingView:
    room = room_service.get_room_or_404(db, room_id)
    membership, meeting = meeting_service.open_meeting(db, room, user)
    media_enabled, media_provider, media_reason = livekit_service.media_status()
    return MeetingView(
        room=_room_summary(db, room, user),
        members=[_member_view(item) for item in room_service.list_members(db, room)],
        role=membership.role,
        user_id=user.id,
        media_enabled=media_enabled,
        media_provider=media_provider,
        media_reason=media_reason,
        meeting_started_at=meeting["meeting_started_at"],
        meeting_ended_at=meeting["meeting_ended_at"],
        elapsed_seconds=meeting["elapsed_seconds"],
        meeting_running=meeting["running"],
        unread_messages=chat_service.unread_count(db, room, user),
    )


@router.post("/rooms/{room_id}/livekit-token", response_model=LiveKitTokenView)
def issue_livekit_token(
    room_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LiveKitTokenView:
    settings = get_settings()
    check_rate_limit(_client_key(request, "livekit"), settings.rate_limit_livekit_per_minute)
    room = room_service.get_room_or_404(db, room_id)
    membership = room_service.require_room_access(db, room, user)
    payload = livekit_service.create_access_token(room, user, membership)
    return LiveKitTokenView(**payload)
