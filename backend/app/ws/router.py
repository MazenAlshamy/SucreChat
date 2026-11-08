import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.config import get_settings
from app.database import get_session_factory
from app.models import JoinRequest, Room
from app.services import identity as identity_service
from app.services import livekit as livekit_service
from app.services import rooms as room_service
from app.ws.hub import SocketClient, hub
from app.ws.payloads import event, join_request_payload, member_payload, room_payload
from app.services import chat as chat_service
from app.services import meetings as meeting_service
from app.ws.publish import (
    notify_presence_members,
    publish_presence,
    request_channel,
    room_channel,
    user_channel,
)

router = APIRouter(tags=["websocket"])
POLICY = status.WS_1008_POLICY_VIOLATION


async def _close(websocket: WebSocket, code: int = POLICY) -> None:
    try:
        await websocket.close(code=code)
    except Exception:
        pass


@router.websocket("/api/ws/rooms/{room_id}")
async def room_socket(websocket: WebSocket, room_id: str) -> None:
    db = get_session_factory()()
    client: SocketClient | None = None
    try:
        user = identity_service.resolve_user_from_token(
            db, websocket.cookies.get(get_settings().session_cookie_name)
        )
        room = db.get(Room, room_id)
        membership = (
            room_service.get_membership(db, room.id, user.id) if user and room else None
        )
        await websocket.accept()
        if user is None or room is None or membership is None:
            await _close(websocket)
            return
        if room.status == "closed" and membership.role != "owner":
            await _close(websocket)
            return

        client = SocketClient(
            websocket=websocket,
            user_id=user.id,
            role=membership.role,
            display_name=membership.display_name,
            channel=room_channel(room.id),
        )
        first = await hub.join(client)
        pending = 0
        if membership.role == "owner":
            pending = sum(1 for item in room.join_requests if item.status == "pending")
        media_enabled, media_provider, media_reason = livekit_service.media_status()
        meeting = meeting_service.meeting_payload(room)
        await websocket.send_json(
            event(
                "connected",
                room=room_payload(
                    room,
                    room_service.active_member_count(db, room.id),
                    pending,
                    membership.role == "owner",
                ),
                members=[member_payload(item) for item in room_service.list_members(db, room)],
                role=membership.role,
                user_id=user.id,
                online_users=hub.online_users(client.channel),
                media_enabled=media_enabled,
                media_provider=media_provider,
                media_reason=media_reason,
                meeting_started_at=meeting["meeting_started_at"],
                elapsed_seconds=meeting["elapsed_seconds"],
                meeting_running=meeting["running"],
            )
        )
        if first:
            publish_presence(room.id, "join", user.id, membership.display_name, membership.role)
            notify_presence_members(db, room, "join", user.id, membership.display_name)
            try:
                db.commit()
            except Exception:
                db.rollback()

        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(event("error", message="رسالة غير صالحة"))
                continue
            message_type = message.get("type")
            if message_type == "ping":
                await websocket.send_json(event("pong"))
            elif message_type == "leave":
                break
            elif message_type == "chat":
                body = message.get("body") or message.get("text") or ""
                try:
                    saved = chat_service.create_message(db, room, user, str(body))
                    db.commit()
                    await websocket.send_json(
                        event("chat_ack", message=chat_service.message_payload(saved, user.id))
                    )
                except Exception as exc:
                    db.rollback()
                    detail = getattr(exc, "detail", None)
                    text = detail.get("message") if isinstance(detail, dict) else "تعذر إرسال الرسالة"
                    await websocket.send_json(event("error", message=text))
            elif message_type == "signal":
                action = message.get("action")
                if action not in {
                    "join-media",
                    "leave-media",
                    "offer",
                    "answer",
                    "ice",
                    "media-state",
                    "screen-start",
                    "screen-stop",
                }:
                    await websocket.send_json(event("error", message="إشارة غير مدعومة"))
                    continue
                target = message.get("to_user")
                if target is not None and (not isinstance(target, str) or not target or target == user.id):
                    await websocket.send_json(event("error", message="المستقبل غير صالح"))
                    continue
                current = db.get(Room, room_id)
                if current is None or current.status != "active":
                    await websocket.send_json(event("error", message="الغرفة مغلقة ولا يمكن تبادل الوسائط"))
                    continue
                if room_service.get_membership(db, room_id, user.id) is None:
                    await websocket.send_json(event("error", message="ليست لديك عضوية معتمدة في هذه الغرفة"))
                    continue
                data = message.get("data")
                state = message.get("state")
                if data is not None and not isinstance(data, (dict, list, str, int, float, bool)):
                    await websocket.send_json(event("error", message="بيانات الإشارة غير صالحة"))
                    continue
                if state is not None and not isinstance(state, dict):
                    await websocket.send_json(event("error", message="حالة الوسائط غير صالحة"))
                    continue
                if action == "join-media":
                    existing = hub.mark_media_join(client.channel, user.id)
                    await websocket.send_json(
                        event(
                            "signal",
                            action="media-peers",
                            peers=existing,
                            from_user=user.id,
                        )
                    )
                elif action == "leave-media":
                    hub.mark_media_leave(client.channel, user.id)
                payload = event(
                    "signal",
                    action=action,
                    from_user=user.id,
                    display_name=membership.display_name,
                    to_user=target,
                    data=data,
                    state=state,
                )
                await hub.broadcast(
                    client.channel,
                    payload,
                    to_user=target,
                    exclude_user=None if target else user.id,
                )
            elif message_type in {"decision", "approve", "reject", "admin"}:
                await websocket.send_json(
                    event("error", message="الأحداث الإدارية غير مسموحة عبر هذه القناة")
                )
            else:
                await websocket.send_json(event("error", message="نوع الحدث غير مدعوم"))
    except WebSocketDisconnect:
        pass
    finally:
        if client is not None:
            last = await hub.leave(client)
            if last:
                publish_presence(room_id, "leave", client.user_id, client.display_name, client.role)
                current = db.get(Room, room_id)
                if current is not None:
                    notify_presence_members(db, current, "leave", client.user_id, client.display_name)
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()
        db.close()


@router.websocket("/api/ws/join-requests/{request_id}")
async def request_socket(websocket: WebSocket, request_id: str) -> None:
    db = get_session_factory()()
    client: SocketClient | None = None
    try:
        user = identity_service.resolve_user_from_token(
            db, websocket.cookies.get(get_settings().session_cookie_name)
        )
        item = db.get(JoinRequest, request_id)
        await websocket.accept()
        if user is None or item is None or item.user_id != user.id:
            await _close(websocket)
            return

        client = SocketClient(
            websocket=websocket,
            user_id=user.id,
            role="applicant",
            display_name=item.display_name,
            channel=request_channel(item.id),
        )
        await hub.join(client)
        room_name = item.room.name if item.room else None
        await websocket.send_json(event("connected", request=join_request_payload(item, room_name)))

        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(event("error", message="رسالة غير صالحة"))
                continue
            message_type = message.get("type")
            if message_type == "ping":
                await websocket.send_json(event("pong"))
            elif message_type == "leave":
                break
            elif message_type in {"decision", "approve", "reject"}:
                await websocket.send_json(
                    event("error", message="لا يمكن تغيير حالة الطلب من هذه القناة")
                )
            else:
                await websocket.send_json(event("error", message="نوع الحدث غير مدعوم"))
    except WebSocketDisconnect:
        pass
    finally:
        if client is not None:
            await hub.leave(client)
        db.close()


@router.websocket("/api/ws/inbox")
async def inbox_socket(websocket: WebSocket) -> None:
    db = get_session_factory()()
    client: SocketClient | None = None
    try:
        user = identity_service.resolve_user_from_token(
            db, websocket.cookies.get(get_settings().session_cookie_name)
        )
        await websocket.accept()
        if user is None:
            await _close(websocket)
            return
        client = SocketClient(
            websocket=websocket,
            user_id=user.id,
            role="inbox",
            display_name=user.display_name,
            channel=user_channel(user.id),
        )
        await hub.join(client)
        await websocket.send_json(event("connected", user_id=user.id))
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(event("error", message="رسالة غير صالحة"))
                continue
            message_type = message.get("type")
            if message_type == "ping":
                await websocket.send_json(event("pong"))
            elif message_type == "leave":
                break
            else:
                await websocket.send_json(event("error", message="نوع الحدث غير مدعوم"))
    except WebSocketDisconnect:
        pass
    finally:
        if client is not None:
            await hub.leave(client)
        db.close()
