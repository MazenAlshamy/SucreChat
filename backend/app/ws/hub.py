from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass

from fastapi import WebSocket


@dataclass
class SocketClient:
    websocket: WebSocket
    user_id: str
    role: str
    display_name: str
    channel: str
    online: bool = True


class Hub:
    def __init__(self) -> None:
        self._channels: dict[str, list[SocketClient]] = defaultdict(list)
        self._media: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join(self, client: SocketClient) -> bool:
        async with self._lock:
            first = not any(
                item.user_id == client.user_id for item in self._channels[client.channel]
            )
            self._channels[client.channel].append(client)
            return first

    async def leave(self, client: SocketClient) -> bool:
        async with self._lock:
            clients = self._channels.get(client.channel, [])
            self._channels[client.channel] = [item for item in clients if item is not client]
            if not self._channels[client.channel]:
                self._channels.pop(client.channel, None)
            still_online = any(
                item.user_id == client.user_id for item in self._channels.get(client.channel, [])
            )
            if not still_online:
                peers = self._media.get(client.channel)
                if peers is not None:
                    peers.discard(client.user_id)
                    if not peers:
                        self._media.pop(client.channel, None)
            return not still_online

    def online_users(self, channel: str) -> list[dict]:
        seen: dict[str, dict] = {}
        for client in self._channels.get(channel, []):
            seen[client.user_id] = {
                "user_id": client.user_id,
                "display_name": client.display_name,
                "role": client.role,
            }
        return list(seen.values())

    def is_online(self, channel: str, user_id: str) -> bool:
        return any(item.user_id == user_id for item in self._channels.get(channel, []))

    def mark_media_join(self, channel: str, user_id: str) -> list[dict]:
        peers = self._media[channel]
        existing: list[dict] = []
        seen: set[str] = set()
        for client in self._channels.get(channel, []):
            if client.user_id in peers and client.user_id != user_id and client.user_id not in seen:
                seen.add(client.user_id)
                existing.append(
                    {
                        "user_id": client.user_id,
                        "display_name": client.display_name,
                    }
                )
        peers.add(user_id)
        return existing

    def mark_media_leave(self, channel: str, user_id: str) -> bool:
        peers = self._media.get(channel)
        if not peers or user_id not in peers:
            return False
        peers.discard(user_id)
        if not peers:
            self._media.pop(channel, None)
        return True

    def is_in_media(self, channel: str, user_id: str) -> bool:
        return user_id in self._media.get(channel, set())

    async def broadcast(
        self,
        channel: str,
        event: dict,
        *,
        to_user: str | None = None,
        owner_only: bool = False,
        exclude_user: str | None = None,
    ) -> None:
        recipients = list(self._channels.get(channel, []))
        stale: list[SocketClient] = []
        for client in recipients:
            if to_user and client.user_id != to_user:
                continue
            if exclude_user and client.user_id == exclude_user:
                continue
            if owner_only and client.role != "owner":
                continue
            try:
                await client.websocket.send_json(event)
            except Exception:
                stale.append(client)
        for client in stale:
            await self.leave(client)

    async def close_non_owners(self, channel: str) -> None:
        recipients = list(self._channels.get(channel, []))
        for client in recipients:
            if client.role == "owner":
                continue
            try:
                await client.websocket.close(code=1008)
            except Exception:
                pass
            await self.leave(client)

    def clear(self) -> None:
        self._channels.clear()
        self._media.clear()


hub = Hub()


def reset_hub() -> None:
    hub.clear()
