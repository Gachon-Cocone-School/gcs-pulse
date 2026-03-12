from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.core.config import settings
from app import crud
from app.database import AsyncSessionLocal
from app.lib.notification_runtime import NotificationSession, registry
from app.limiter import limiter
from app.utils_time import to_business_timezone

try:
    from sse_starlette import EventSourceResponse
except ModuleNotFoundError:  # pragma: no cover - fallback for local envs without dependency installed
    EventSourceResponse = None


router = APIRouter(prefix="/notifications", tags=["notifications-sse"])

HEARTBEAT_INTERVAL_SECONDS = 15


def _now_iso() -> str:
    return to_business_timezone(datetime.now().astimezone()).isoformat()


def _sse_event(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"event": event, "data": json.dumps(payload, ensure_ascii=False)}


def _serialize_sse(event: dict[str, Any]) -> bytes:
    lines: list[str] = []

    event_name = event.get("event")
    if event_name:
        lines.append(f"event: {event_name}")

    raw_data = event.get("data", "")
    if isinstance(raw_data, (dict, list)):
        data = json.dumps(raw_data, ensure_ascii=False)
    else:
        data = str(raw_data)

    for line in data.splitlines() or [""]:
        lines.append(f"data: {line}")

    return ("\n".join(lines) + "\n\n").encode("utf-8")


async def _fallback_stream(source: AsyncIterator[dict[str, Any]]) -> AsyncIterator[bytes]:
    async for event in source:
        yield _serialize_sse(event)


async def _notifications_event_stream(
    request: Request,
    session: NotificationSession,
) -> AsyncIterator[dict[str, Any]]:
    try:
        yield _sse_event(
            "session",
            {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
            },
        )

        while True:
            if await request.is_disconnected():
                break

            try:
                event = await asyncio.wait_for(
                    session.queue.get(),
                    timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                yield _sse_event("heartbeat", {"now": _now_iso()})
                continue

            yield event
    finally:
        await registry.remove(session.session_id)


async def _get_logged_in_user_or_401(request: Request):
    email = (request.session.get("user") or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with AsyncSessionLocal() as db:
        user = await crud.get_user_by_email_basic(db, str(email).strip().lower())

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/sse")
@limiter.limit(settings.NOTIFICATIONS_SSE_LIMIT)
async def connect_notifications_sse(
    request: Request,
):
    viewer = await _get_logged_in_user_or_401(request)
    session = await registry.create(user_id=viewer.id)
    stream = _notifications_event_stream(request, session)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }

    if EventSourceResponse is not None:
        return EventSourceResponse(stream, headers=headers)

    return StreamingResponse(
        _fallback_stream(stream),
        media_type="text/event-stream",
        headers=headers,
    )
