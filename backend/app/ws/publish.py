from __future__ import annotations

import asyncio

import anyio
from sqlalchemy.orm import Session

from app.models import JoinRequest, Room
from app.services import rooms as room_service
from app.ws.hub import hub
from app.ws.payloads import event, join_request_payload, member_payload, room_payload


async def _broadcast(
    channel: str,
    payload: dict,
    to_user: str | None = None,
    owner_only: bool = False,
    exclude_user: str | None = None,
) -> None:
    await hub.broadcast(
        channel,
        payload,
        to_user=to_user,
        owner_only=owner_only,
        exclude_user=exclude_user,
    )


def publish(
    channel: str,
    payload: dict,
    *,
    to_user: str | None = None,
    owner_only: bool = False,
    exclude_user: str | None = None,
) -> None:
    try:
        anyio.from_thread.run(_broadcast, channel, payload, to_user, owner_only, exclude_user)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_broadcast(channel, payload, to_user, owner_only, exclude_user))
        else:
            loop.run_until_complete(_broadcast(channel, payload, to_user, owner_only, exclude_user))


def room_channel(room_id: str) -> str:
    return f"room:{room_id}"


def request_channel(request_id: str) -> str:
    return f"request:{request_id}"


def user_channel(user_id: str) -> str:
    return f"user:{user_id}"


def publish_user_event(user_id: str, payload: dict) -> None:
    publish(user_channel(user_id), payload, to_user=user_id)


def publish_room_chat(room_id: str, message: dict) -> None:
    publish(room_channel(room_id), event("chat_message", message=message))


def _summary(db: Session, room: Room, pending: int = 0, is_owner: bool = False) -> dict:
    return room_payload(
        room,
        room_service.active_member_count(db, room.id),
        pending,
        is_owner,
    )


def publish_join_request(db: Session, item: JoinRequest, room: Room) -> None:
    from app.services import notifications as notification_service

    payload = join_request_payload(item, room.name)
    pending = sum(1 for entry in room.join_requests if entry.status == "pending")
    publish(
        room_channel(room.id),
        event("join_request", request=payload, room=_summary(db, room, pending, True)),
        owner_only=True,
    )
    publish(
        request_channel(item.id),
        event("request_updated", request=payload),
        to_user=item.user_id,
    )
    notification_service.notify_users(
        db,
        [room.owner_id],
        ntype="join_request",
        title="طلب انضمام جديد",
        body=f"{item.display_name} يطلب الانضمام إلى {room.name}",
        link=f"/rooms/{room.id}#join-requests",
        room=room,
        join_request_id=item.id,
        exclude_user=item.user_id,
    )


def publish_request_decision(db: Session, item: JoinRequest, room: Room) -> None:
    from app.services import notifications as notification_service

    members = [member_payload(member) for member in room_service.list_members(db, room)]
    payload = join_request_payload(item, room.name)
    pending = sum(1 for entry in room.join_requests if entry.status == "pending")
    publish(
        room_channel(room.id),
        event(
            "request_updated",
            request=payload,
            members=members,
            room=_summary(db, room, pending, True),
        ),
        owner_only=True,
    )
    publish(
        room_channel(room.id),
        event(
            "members_updated",
            members=members,
            room=_summary(db, room),
        ),
    )
    publish(
        request_channel(item.id),
        event("request_updated", request=payload),
        to_user=item.user_id,
    )
    if item.status == "approved":
        notification_service.notify_users(
            db,
            [item.user_id],
            ntype="join_approved",
            title="تمت الموافقة على طلبك",
            body=f"يمكنك دخول غرفة {room.name}",
            link=f"/rooms/{room.id}/meeting",
            room=room,
            join_request_id=item.id,
        )
    elif item.status == "rejected":
        notification_service.notify_users(
            db,
            [item.user_id],
            ntype="join_rejected",
            title="رُفض طلب الانضمام",
            body=f"رفض مالك الغرفة طلبك لدخول {room.name}",
            link="/join",
            room=room,
            join_request_id=item.id,
        )


async def _publish_room_updated(channel: str, payload: dict, close_members: bool) -> None:
    await hub.broadcast(channel, payload)
    if close_members:
        await hub.close_non_owners(channel)


def publish_room_updated(db: Session, room: Room) -> None:
    members = [member_payload(member) for member in room_service.list_members(db, room)]
    pending = sum(1 for entry in room.join_requests if entry.status == "pending")
    payload = event("room_updated", room=_summary(db, room, pending), members=members)
    channel = room_channel(room.id)
    close_members = room.status == "closed"
    try:
        anyio.from_thread.run(_publish_room_updated, channel, payload, close_members)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_publish_room_updated(channel, payload, close_members))
        else:
            loop.run_until_complete(_publish_room_updated(channel, payload, close_members))


def publish_presence(room_id: str, action: str, user_id: str, display_name: str, role: str) -> None:
    publish(
        room_channel(room_id),
        event(
            "presence",
            action=action,
            user_id=user_id,
            display_name=display_name,
            role=role,
            online_users=hub.online_users(room_channel(room_id)),
        ),
        exclude_user=user_id,
    )


def notify_presence_members(
    db: Session,
    room: Room,
    action: str,
    actor_id: str,
    display_name: str,
) -> None:
    from app.services import notifications as notification_service

    members = room_service.list_members(db, room)
    verb = "دخل" if action == "join" else "غادر"
    notification_service.notify_users(
        db,
        [member.user_id for member in members],
        ntype="presence_join" if action == "join" else "presence_leave",
        title=f"{verb} مشارك",
        body=f"{display_name} {verb} غرفة {room.name}",
        link=f"/rooms/{room.id}/meeting",
        room=room,
        exclude_user=actor_id,
    )
