from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from mcp import types as mcp_types
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.database import get_db
from app.lib.mcp_runtime import McpSession, registry
from app.routers.snippet_access import BearerAuthContext, get_bearer_auth_or_401
from app.utils_time import to_business_timezone

try:
    from sse_starlette import EventSourceResponse
except ModuleNotFoundError:  # pragma: no cover - fallback for local envs without dependency installed
    EventSourceResponse = None


router = APIRouter(prefix="/mcp", tags=["mcp"])

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


async def get_mcp_user_from_bearer(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> BearerAuthContext:
    return await get_bearer_auth_or_401(request, db)


async def _mcp_event_stream(request: Request, session: McpSession) -> AsyncIterator[dict[str, Any]]:
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


@router.get("/sse")
async def connect_mcp_sse(
    request: Request,
    auth: BearerAuthContext = Depends(get_mcp_user_from_bearer),
):
    session = await registry.create(user_id=auth.user.id)
    stream = _mcp_event_stream(request, session)

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


@router.post("/messages")
async def post_mcp_message(
    request: Request,
    session_id: str = Query(...),
    auth: BearerAuthContext = Depends(get_mcp_user_from_bearer),
):
    session = await registry.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="MCP session not found")

    if session.user_id != auth.user.id:
        raise HTTPException(status_code=403, detail="MCP session forbidden")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Invalid MCP message")

    try:
        parsed_message = mcp_types.JSONRPCMessage.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Invalid MCP message") from exc

    normalized_message = parsed_message.model_dump(by_alias=True, exclude_none=True)

    await registry.send(
        session_id,
        _sse_event(
            "message",
            {
                "session_id": session_id,
                "message": normalized_message,
            },
        ),
    )

    return {"ok": True, "session_id": session_id}
