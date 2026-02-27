from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.utils_time import to_business_timezone


@dataclass(slots=True)
class NotificationSession:
    session_id: str
    user_id: int
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    created_at: datetime = field(
        default_factory=lambda: to_business_timezone(datetime.now().astimezone())
    )


class NotificationSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, NotificationSession] = {}
        self._lock = asyncio.Lock()

    async def create(self, user_id: int) -> NotificationSession:
        session = NotificationSession(session_id=str(uuid4()), user_id=user_id)
        async with self._lock:
            self._sessions[session.session_id] = session
        return session

    async def get(self, session_id: str) -> NotificationSession | None:
        async with self._lock:
            return self._sessions.get(session_id)

    async def remove(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def send(self, session_id: str, event: dict[str, Any]) -> bool:
        session = await self.get(session_id)
        if not session:
            return False
        await session.queue.put(event)
        return True

    async def send_to_user(self, user_id: int, event: dict[str, Any]) -> None:
        async with self._lock:
            target_sessions = [
                session for session in self._sessions.values() if session.user_id == user_id
            ]

        for session in target_sessions:
            await session.queue.put(event)


registry = NotificationSessionRegistry()
