from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import bad_request, conflict, forbidden, not_found
from app.models import Invitation, JoinRequest, Room, RoomMember, User
from app.security import as_utc, generate_invite_code, hash_token, invite_prefix, new_id, utcnow


def validate_room_payload(name: str, description: str | None, max_participants: int | None) -> tuple[str, str | None, int]:
    settings = get_settings()
    cleaned_name = (name or "").strip()
    if len(cleaned_name) < settings.room_name_min_length:
        raise bad_request("اسم الغرفة قصير جداً")
    if len(cleaned_name) > settings.room_name_max_length:
        raise bad_request("اسم الغرفة طويل جداً")

    cleaned_description = (description or "").strip() or None
    if cleaned_description and len(cleaned_description) > settings.room_description_max_length:
        raise bad_request("وصف الغرفة طويل جداً")

    limit = max_participants if max_participants is not None else settings.room_max_participants_default
    if limit < settings.room_max_participants_min or limit > settings.room_max_participants_limit:
        raise bad_request("الحد الأقصى للمشاركين غير صالح")
    return cleaned_name, cleaned_description, limit


def validate_display_name(display_name: str) -> str:
    settings = get_settings()
    cleaned = "".join(ch for ch in (display_name or "") if ch.isprintable()).strip()
    if len(cleaned) < settings.display_name_min_length:
        raise bad_request("اسم العرض قصير جداً")
    if len(cleaned) > settings.display_name_max_length:
        raise bad_request("اسم العرض طويل جداً")
    return cleaned


def active_member_count(db: Session, room_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(RoomMember).where(
            RoomMember.room_id == room_id,
            RoomMember.status == "active",
        )
    ) or 0


def get_membership(db: Session, room_id: str, user_id: str) -> RoomMember | None:
    return db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user_id,
        RoomMember.status == "active",
    ).one_or_none()


def is_owner(room: Room, user: User) -> bool:
    return room.owner_id == user.id


def require_owner(room: Room, user: User) -> None:
    if not is_owner(room, user):
        raise forbidden("هذه العملية متاحة لمالك الغرفة فقط")


def get_room_or_404(db: Session, room_id: str) -> Room:
    room = db.get(Room, room_id)
    if room is None:
        raise not_found("الغرفة غير موجودة")
    return room


def create_room(
    db: Session,
    owner: User,
    name: str,
    description: str | None,
    max_participants: int | None,
    allow_guest_requests: bool = True,
) -> Room:
    cleaned_name, cleaned_description, limit = validate_room_payload(name, description, max_participants)
    room = Room(
        id=new_id(),
        name=cleaned_name,
        description=cleaned_description,
        owner_id=owner.id,
        status="active",
        max_participants=limit,
        allow_guest_requests=allow_guest_requests,
    )
    db.add(room)
    db.flush()
    member = RoomMember(
        id=new_id(),
        room_id=room.id,
        user_id=owner.id,
        role="owner",
        status="active",
        display_name=owner.display_name,
    )
    db.add(member)
    db.flush()
    return room


def close_room(db: Session, room: Room, user: User) -> Room:
    require_owner(room, user)
    if room.status == "closed":
        return room
    room.status = "closed"
    if room.meeting_started_at and room.meeting_ended_at is None:
        room.meeting_ended_at = utcnow()
    db.flush()
    return room


def invitation_is_usable(invitation: Invitation) -> tuple[bool, str]:
    now = utcnow()
    if invitation.status == "revoked":
        return False, "الدعوة مبطلة"
    expires_at = as_utc(invitation.expires_at)
    if expires_at is not None and expires_at <= now:
        invitation.status = "expired"
        return False, "انتهت صلاحية الدعوة"
    if invitation.max_uses is not None and invitation.use_count >= invitation.max_uses:
        invitation.status = "exhausted"
        return False, "تجاوزت الدعوة حد الاستخدام"
    if invitation.status != "active":
        return False, "الدعوة غير صالحة"
    return True, ""


def create_invitation(
    db: Session,
    room: Room,
    creator: User,
    max_uses: int | None,
    expires_in_hours: int | None,
) -> tuple[Invitation, str]:
    require_owner(room, creator)
    if room.status != "active":
        raise bad_request("لا يمكن إنشاء دعوة لغرفة مغلقة")
    settings = get_settings()
    if max_uses is not None and (max_uses < 1 or max_uses > settings.invite_max_uses_limit):
        raise bad_request("حد استخدام الدعوة غير صالح")
    if expires_in_hours is not None and (expires_in_hours < 1 or expires_in_hours > 24 * 30):
        raise bad_request("مدة صلاحية الدعوة غير صالحة")

    code = generate_invite_code()
    invitation = Invitation(
        id=new_id(),
        room_id=room.id,
        created_by=creator.id,
        code_hash=hash_token(code),
        code_prefix=invite_prefix(code),
        status="active",
        max_uses=max_uses,
        use_count=0,
        expires_at=utcnow() + timedelta(hours=expires_in_hours) if expires_in_hours else None,
    )
    db.add(invitation)
    db.flush()
    return invitation, code


def get_invitation_by_code(db: Session, code: str) -> Invitation | None:
    if not code:
        return None
    return db.query(Invitation).filter(Invitation.code_hash == hash_token(code.strip())).one_or_none()


def revoke_invitation(db: Session, invitation: Invitation, user: User) -> Invitation:
    room = get_room_or_404(db, invitation.room_id)
    require_owner(room, user)
    if invitation.status == "revoked":
        return invitation
    invitation.status = "revoked"
    invitation.revoked_at = utcnow()
    db.flush()
    return invitation


def public_invite_payload(invitation: Invitation, room: Room) -> dict:
    usable, reason = invitation_is_usable(invitation)
    return {
        "valid": usable,
        "reason": None if usable else reason,
        "room_name": room.name if usable else None,
        "room_status": room.status if usable else None,
        "max_participants": room.max_participants if usable else None,
        "description": room.description if usable else None,
        "expires_at": invitation.expires_at if usable else None,
    }


def submit_join_request(
    db: Session,
    user: User,
    code: str,
    display_name: str,
) -> JoinRequest:
    cleaned_name = validate_display_name(display_name)
    user.display_name = cleaned_name
    invitation = get_invitation_by_code(db, code)
    if invitation is None:
        raise not_found("الدعوة غير صالحة")

    room = get_room_or_404(db, invitation.room_id)
    membership = get_membership(db, room.id, user.id)
    if membership is not None:
        raise conflict("أنت عضو معتمد في هذه الغرفة بالفعل", room_id=room.id, status="approved")

    existing = db.query(JoinRequest).filter(
        JoinRequest.room_id == room.id,
        JoinRequest.user_id == user.id,
    ).one_or_none()
    if existing is not None and existing.status == "pending":
        existing.display_name = cleaned_name
        existing.invitation_id = invitation.id
        db.flush()
        return existing

    usable, reason = invitation_is_usable(invitation)
    if not usable:
        raise forbidden(reason)
    if room.status != "active":
        raise forbidden("الغرفة مغلقة")
    if not room.allow_guest_requests:
        raise forbidden("هذه الغرفة لا تقبل طلبات انضمام جديدة")
    if existing is not None:
        if existing.status == "pending":
            existing.display_name = cleaned_name
            existing.invitation_id = invitation.id
            db.flush()
            return existing
        if existing.status == "approved":
            raise conflict("تمت الموافقة على طلبك مسبقاً", room_id=room.id, status="approved")
        if existing.status == "rejected":
            raise forbidden("تم رفض طلبك مسبقاً ولا يمكن إعادة التقديم بهذه الدعوة")
        if existing.status == "cancelled":
            existing.status = "pending"
            existing.display_name = cleaned_name
            existing.invitation_id = invitation.id
            existing.created_at = utcnow()
            existing.decided_at = None
            existing.decided_by = None
            invitation.use_count += 1
            invitation_is_usable(invitation)
            db.flush()
            return existing

    request = JoinRequest(
        id=new_id(),
        room_id=room.id,
        user_id=user.id,
        invitation_id=invitation.id,
        display_name=cleaned_name,
        status="pending",
    )
    invitation.use_count += 1
    invitation_is_usable(invitation)
    db.add(request)
    db.flush()
    return request


def list_join_requests(db: Session, room: Room, user: User) -> list[JoinRequest]:
    require_owner(room, user)
    return (
        db.query(JoinRequest)
        .filter(JoinRequest.room_id == room.id)
        .order_by(JoinRequest.created_at.desc())
        .all()
    )


def decide_join_request(
    db: Session,
    request_id: str,
    owner: User,
    decision: str,
) -> JoinRequest:
    if decision not in {"approved", "rejected"}:
        raise bad_request("قرار غير صالح")

    join_request = db.get(JoinRequest, request_id)
    if join_request is None:
        raise not_found("طلب الانضمام غير موجود")

    room = get_room_or_404(db, join_request.room_id)
    require_owner(room, owner)

    if join_request.status != "pending":
        raise conflict("لا يمكن تعديل طلب لم يعد معلقاً")
    if join_request.user_id == owner.id:
        raise forbidden("لا يمكن للمالك قبول طلبه بهذه الطريقة")

    if decision == "approved":
        if room.status != "active":
            raise forbidden("الغرفة مغلقة")
        if active_member_count(db, room.id) >= room.max_participants:
            raise conflict("وصلت الغرفة إلى الحد الأقصى للمشاركين")
        membership = get_membership(db, room.id, join_request.user_id)
        if membership is None:
            db.add(
                RoomMember(
                    id=new_id(),
                    room_id=room.id,
                    user_id=join_request.user_id,
                    role="member",
                    status="active",
                    display_name=join_request.display_name,
                )
            )

    join_request.status = decision
    join_request.decided_at = utcnow()
    join_request.decided_by = owner.id
    db.flush()
    return join_request


def require_room_access(db: Session, room: Room, user: User) -> RoomMember:
    membership = get_membership(db, room.id, user.id)
    if membership is None:
        raise forbidden("ليست لديك عضوية معتمدة في هذه الغرفة")
    return membership


def list_members(db: Session, room: Room) -> list[RoomMember]:
    return (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room.id, RoomMember.status == "active")
        .order_by(RoomMember.joined_at.asc())
        .all()
    )


def list_invitations(db: Session, room: Room, user: User) -> list[Invitation]:
    require_owner(room, user)
    invitations = (
        db.query(Invitation)
        .filter(Invitation.room_id == room.id)
        .order_by(Invitation.created_at.desc())
        .all()
    )
    for invitation in invitations:
        invitation_is_usable(invitation)
    return invitations


def get_join_request_for_user(db: Session, request_id: str, user: User) -> JoinRequest:
    join_request = db.get(JoinRequest, request_id)
    if join_request is None or join_request.user_id != user.id:
        raise not_found("طلب الانضمام غير موجود")
    return join_request


def list_owned_rooms(db: Session, user: User) -> list[Room]:
    return db.query(Room).filter(Room.owner_id == user.id).order_by(Room.created_at.desc()).all()


def list_member_rooms(db: Session, user: User) -> list[Room]:
    return (
        db.query(Room)
        .join(RoomMember, RoomMember.room_id == Room.id)
        .filter(RoomMember.user_id == user.id, RoomMember.status == "active")
        .order_by(Room.created_at.desc())
        .all()
    )
