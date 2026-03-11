from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app import crud, crud_mentoring, schemas
from app.database import get_db
from app.dependencies import require_professor_role, verify_csrf
from app.routers import snippet_utils
from app.services.mentoring_agent_service import MentoringAgentService
from app.services.mentoring_memory_service import (
    get_or_create_professor_memory,
    update_professor_memory,
)

try:
    from sse_starlette import EventSourceResponse
except ModuleNotFoundError:  # pragma: no cover
    EventSourceResponse = None


router = APIRouter(
    prefix="/professor/mentoring",
    tags=["mentoring-chat"],
    dependencies=[Depends(verify_csrf)],
)

HEARTBEAT_INTERVAL_SECONDS = 15


async def _get_professor_or_403(request: Request, db: AsyncSession):
    email = (request.session.get("user") or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await crud.get_user_by_email_basic(db, str(email).strip().lower())
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    require_professor_role(user)
    return user


def _serialize_sse(event: dict[str, Any]) -> bytes:
    lines: list[str] = []
    if event.get("event"):
        lines.append(f"event: {event['event']}")

    data = event.get("data", "")
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)

    for line in data.splitlines() or [""]:
        lines.append(f"data: {line}")

    return ("\n".join(lines) + "\n\n").encode("utf-8")


async def _fallback_stream(source: AsyncIterator[dict[str, Any]]) -> AsyncIterator[bytes]:
    async for event in source:
        yield _serialize_sse(event)


async def _build_action_response(action) -> schemas.MentoringActionLogResponse:
    return schemas.MentoringActionLogResponse(
        id=action.id,
        session_id=action.session_id,
        message_id=action.message_id,
        action_type=action.action_type,
        status=action.status,
        action_payload_json=action.action_payload_json,
        approved_by_user_id=action.approved_by_user_id,
        executed_at=action.executed_at,
        error_message=action.error_message,
        created_at=action.created_at,
    )


async def _execute_comment_action_or_400(
    db: AsyncSession,
    *,
    professor,
    payload: dict[str, Any],
) -> dict[str, Any]:
    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=400, detail="Action payload must include non-empty content")

    daily_snippet_raw = payload.get("daily_snippet_id")
    weekly_snippet_raw = payload.get("weekly_snippet_id")
    has_daily = isinstance(daily_snippet_raw, int)
    has_weekly = isinstance(weekly_snippet_raw, int)
    if has_daily == has_weekly:
        raise HTTPException(
            status_code=400,
            detail="Action payload must include exactly one of daily_snippet_id or weekly_snippet_id",
        )

    daily_snippet_id = daily_snippet_raw if has_daily else None
    weekly_snippet_id = weekly_snippet_raw if has_weekly else None

    if daily_snippet_id is not None:
        snippet = await crud.get_daily_snippet_by_id(db, daily_snippet_id)
        if snippet is None:
            raise HTTPException(status_code=404, detail="Daily snippet not found")
        owner = snippet.user
    else:
        if weekly_snippet_id is None:
            raise HTTPException(status_code=400, detail="Weekly snippet id is required")
        snippet = await crud.get_weekly_snippet_by_id(db, weekly_snippet_id)
        if snippet is None:
            raise HTTPException(status_code=404, detail="Weekly snippet not found")
        owner = snippet.user

    if owner is None or not snippet_utils.can_read_snippet(professor, owner):
        raise HTTPException(status_code=403, detail="Access denied")

    comment_type_raw = payload.get("comment_type")
    if comment_type_raw not in ("peer", "professor"):
        comment_type_raw = "professor"

    comment = await crud.create_comment(
        db,
        user_id=professor.id,
        content=content.strip(),
        daily_snippet_id=daily_snippet_id if has_daily else None,
        weekly_snippet_id=weekly_snippet_id if has_weekly else None,
        comment_type=comment_type_raw,
    )

    return {
        "executed_comment_id": comment.id,
        "daily_snippet_id": comment.daily_snippet_id,
        "weekly_snippet_id": comment.weekly_snippet_id,
        "comment_type": comment.comment_type,
    }


@router.post("/sessions", response_model=schemas.MentoringChatSessionResponse)
async def create_session(
    payload: schemas.MentoringChatSessionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    title = (payload.title or "새 멘토링 세션").strip() or "새 멘토링 세션"
    row = await crud_mentoring.create_session(
        db,
        professor_user_id=professor.id,
        title=title,
    )
    return schemas.MentoringChatSessionResponse(
        id=row.id,
        professor_user_id=row.professor_user_id,
        title=row.title,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/sessions", response_model=schemas.MentoringChatSessionListResponse)
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    rows = await crud_mentoring.list_sessions_by_professor(db, professor_user_id=professor.id)
    return schemas.MentoringChatSessionListResponse(
        items=[
            schemas.MentoringChatSessionResponse(
                id=row.id,
                professor_user_id=row.professor_user_id,
                title=row.title,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ],
        total=len(rows),
    )


@router.get("/sessions/{session_id}/messages", response_model=schemas.MentoringChatMessageListResponse)
async def list_messages(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await crud_mentoring.get_session_by_id_and_professor(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Mentoring session not found")

    rows = await crud_mentoring.list_messages_by_session(db, session_id=session.id)
    return schemas.MentoringChatMessageListResponse(
        items=[
            schemas.MentoringChatMessageResponse(
                id=row.id,
                session_id=row.session_id,
                role=row.role,
                content_markdown=row.content_markdown,
                tokens_input=row.tokens_input,
                tokens_output=row.tokens_output,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=len(rows),
    )


@router.get("/memory", response_model=schemas.MentoringMemoryResponse)
async def get_memory(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    row = await get_or_create_professor_memory(db, professor_user_id=professor.id)
    return schemas.MentoringMemoryResponse(
        professor_user_id=row.professor_user_id,
        memory_markdown=row.memory_markdown,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


@router.put("/memory", response_model=schemas.MentoringMemoryResponse)
async def put_memory(
    payload: schemas.MentoringMemoryUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    row = await update_professor_memory(
        db,
        professor_user_id=professor.id,
        memory_markdown=payload.memory_markdown,
        updated_by="professor",
    )
    return schemas.MentoringMemoryResponse(
        professor_user_id=row.professor_user_id,
        memory_markdown=row.memory_markdown,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


@router.post("/sessions/{session_id}/messages", response_model=schemas.MentoringChatMessageResponse)
async def send_message(
    session_id: int,
    payload: schemas.MentoringChatMessageSendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await crud_mentoring.get_session_by_id_and_professor(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Mentoring session not found")

    user_message = await crud_mentoring.create_message(
        db,
        session_id=session.id,
        role="user",
        content_markdown=payload.content,
    )

    memory = await get_or_create_professor_memory(db, professor_user_id=professor.id)
    agent = MentoringAgentService()
    result = await agent.generate_reply(
        user_message=payload.content,
        memory_markdown=memory.memory_markdown,
    )

    assistant_message = await crud_mentoring.create_message(
        db,
        session_id=session.id,
        role="assistant",
        content_markdown=result.content_markdown,
        tokens_input=result.tokens_input,
        tokens_output=result.tokens_output,
        latency_ms=result.latency_ms,
        tool_calls_json=result.tool_calls,
    )

    await crud_mentoring.create_action_log(
        db,
        session_id=session.id,
        message_id=assistant_message.id,
        action_type="suggest_comment",
        action_payload_json={"source_message_id": user_message.id},
        status="proposed",
    )

    merged_memory = await agent.summarize_memory(
        previous_memory_markdown=memory.memory_markdown,
        user_message=payload.content,
        assistant_message=result.content_markdown,
    )
    await update_professor_memory(
        db,
        professor_user_id=professor.id,
        memory_markdown=merged_memory,
        updated_by="agent",
    )

    return schemas.MentoringChatMessageResponse(
        id=assistant_message.id,
        session_id=assistant_message.session_id,
        role=assistant_message.role,
        content_markdown=assistant_message.content_markdown,
        tokens_input=assistant_message.tokens_input,
        tokens_output=assistant_message.tokens_output,
        latency_ms=assistant_message.latency_ms,
        created_at=assistant_message.created_at,
    )


@router.post("/actions/{action_id}/approve", response_model=schemas.MentoringActionDecisionResponse)
async def approve_action(
    action_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    action = await crud_mentoring.get_action_by_id(db, action_id=action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")

    session = await crud_mentoring.get_session_by_id_and_professor(
        db,
        session_id=action.session_id,
        professor_user_id=professor.id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Mentoring session not found")

    if action.status != "proposed":
        raise HTTPException(status_code=409, detail="Action is not in proposed state")

    execution_result: dict[str, Any] | None = None
    if action.action_type == "post_comment":
        payload = action.action_payload_json or {}
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid action payload")

        try:
            execution_result = await _execute_comment_action_or_400(
                db,
                professor=professor,
                payload=payload,
            )
        except HTTPException as exc:
            action.status = "failed"
            action.approved_by_user_id = professor.id
            action.executed_at = datetime.now().astimezone()
            action.error_message = str(exc.detail)
            await db.commit()
            await db.refresh(action)
            raise

    action.status = "executed"
    action.approved_by_user_id = professor.id
    action.executed_at = datetime.now().astimezone()
    action.error_message = None
    if execution_result is not None:
        merged_payload = dict(action.action_payload_json or {})
        merged_payload["execution_result"] = execution_result
        action.action_payload_json = merged_payload

    await db.commit()
    await db.refresh(action)

    return schemas.MentoringActionDecisionResponse(
        action=await _build_action_response(action),
        message="Action approved and executed",
    )


@router.post("/actions/{action_id}/reject", response_model=schemas.MentoringActionDecisionResponse)
async def reject_action(
    action_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    action = await crud_mentoring.get_action_by_id(db, action_id=action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")

    session = await crud_mentoring.get_session_by_id_and_professor(
        db,
        session_id=action.session_id,
        professor_user_id=professor.id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Mentoring session not found")

    if action.status != "proposed":
        raise HTTPException(status_code=409, detail="Action is not in proposed state")

    action.status = "rejected"
    action.approved_by_user_id = professor.id
    await db.commit()
    await db.refresh(action)

    return schemas.MentoringActionDecisionResponse(
        action=await _build_action_response(action),
        message="Action rejected",
    )


async def _stream_single_reply(
    request: Request,
    *,
    db: AsyncSession,
    professor_id: int,
    session_id: int,
    content: str,
) -> AsyncIterator[dict[str, Any]]:
    session = await crud_mentoring.get_session_by_id_and_professor(
        db,
        session_id=session_id,
        professor_user_id=professor_id,
    )
    if session is None:
        yield {"event": "error", "data": json.dumps({"detail": "Mentoring session not found"})}
        return

    await crud_mentoring.create_message(
        db,
        session_id=session.id,
        role="user",
        content_markdown=content,
    )

    memory = await get_or_create_professor_memory(db, professor_user_id=professor_id)
    agent = MentoringAgentService()

    collected_parts: list[str] = []
    delta_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    result_holder: dict[str, Any] = {}

    async def on_delta(delta: str) -> None:
        collected_parts.append(delta)
        await delta_queue.put(
            {
                "event": "mentoring_chat_delta",
                "data": json.dumps({"delta": delta}, ensure_ascii=False),
            }
        )

    async def run_agent() -> None:
        try:
            result = await agent.generate_reply_streaming(
                user_message=content,
                memory_markdown=memory.memory_markdown,
                on_delta=on_delta,
            )
            result_holder["result"] = result
        except Exception as exc:  # pragma: no cover
            result_holder["error"] = str(exc)
        finally:
            await delta_queue.put(None)

    task = asyncio.create_task(run_agent())

    try:
        while True:
            if await request.is_disconnected():
                task.cancel()
                return
            try:
                event = await asyncio.wait_for(delta_queue.get(), timeout=HEARTBEAT_INTERVAL_SECONDS)
            except TimeoutError:
                yield {"event": "ping", "data": ""}
                continue

            if event is None:
                break
            yield event

        await task

        if "error" in result_holder:
            yield {"event": "error", "data": json.dumps({"detail": result_holder['error']}, ensure_ascii=False)}
            return

        result = result_holder.get("result")
        if result is None:
            yield {
                "event": "error",
                "data": json.dumps({"detail": "에이전트 응답 생성에 실패했습니다."}, ensure_ascii=False),
            }
            return

        assistant_content = "".join(collected_parts)
        assistant = await crud_mentoring.create_message(
            db,
            session_id=session.id,
            role="assistant",
            content_markdown=assistant_content,
            tokens_input=result.tokens_input,
            tokens_output=result.tokens_output,
            latency_ms=result.latency_ms,
            tool_calls_json=result.tool_calls,
        )

        await crud_mentoring.create_action_log(
            db,
            session_id=session.id,
            message_id=assistant.id,
            action_type="suggest_comment",
            action_payload_json={"source_message_id": assistant.id},
            status="proposed",
        )

        merged_memory = await agent.summarize_memory(
            previous_memory_markdown=memory.memory_markdown,
            user_message=content,
            assistant_message=assistant_content,
        )
        await update_professor_memory(
            db,
            professor_user_id=professor_id,
            memory_markdown=merged_memory,
            updated_by="agent",
        )

        yield {
            "event": "mentoring_chat_done",
            "data": json.dumps(
                {
                    "message_id": assistant.id,
                    "session_id": assistant.session_id,
                    "role": assistant.role,
                },
                ensure_ascii=False,
            ),
        }
    finally:
        if not task.done():
            task.cancel()


@router.get("/sessions/{session_id}/events")
async def stream_reply(
    session_id: int,
    request: Request,
    content: str,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    stream = _stream_single_reply(
        request,
        db=db,
        professor_id=professor.id,
        session_id=session_id,
        content=content,
    )

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
