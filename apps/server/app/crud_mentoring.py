from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    MentoringActionLog,
    MentoringChatMessage,
    MentoringChatSession,
)


async def create_session(
    db: AsyncSession,
    *,
    professor_user_id: int,
    title: str,
) -> MentoringChatSession:
    row = MentoringChatSession(
        professor_user_id=professor_user_id,
        title=title,
        status="active",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_sessions_by_professor(
    db: AsyncSession,
    *,
    professor_user_id: int,
) -> list[MentoringChatSession]:
    result = await db.execute(
        select(MentoringChatSession)
        .filter(MentoringChatSession.professor_user_id == professor_user_id)
        .order_by(MentoringChatSession.updated_at.desc(), MentoringChatSession.id.desc())
    )
    return list(result.scalars().all())


async def get_session_by_id_and_professor(
    db: AsyncSession,
    *,
    session_id: int,
    professor_user_id: int,
) -> MentoringChatSession | None:
    result = await db.execute(
        select(MentoringChatSession).filter(
            MentoringChatSession.id == session_id,
            MentoringChatSession.professor_user_id == professor_user_id,
        )
    )
    return result.scalars().first()


async def create_message(
    db: AsyncSession,
    *,
    session_id: int,
    role: str,
    content_markdown: str,
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    latency_ms: int | None = None,
    tool_calls_json: list[dict] | None = None,
) -> MentoringChatMessage:
    row = MentoringChatMessage(
        session_id=session_id,
        role=role,
        content_markdown=content_markdown,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        latency_ms=latency_ms,
        tool_calls_json=tool_calls_json,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_messages_by_session(
    db: AsyncSession,
    *,
    session_id: int,
) -> list[MentoringChatMessage]:
    result = await db.execute(
        select(MentoringChatMessage)
        .filter(MentoringChatMessage.session_id == session_id)
        .order_by(MentoringChatMessage.created_at.asc(), MentoringChatMessage.id.asc())
    )
    return list(result.scalars().all())


async def create_action_log(
    db: AsyncSession,
    *,
    session_id: int,
    message_id: int | None,
    action_type: str,
    action_payload_json: dict | None,
    status: str = "proposed",
) -> MentoringActionLog:
    row = MentoringActionLog(
        session_id=session_id,
        message_id=message_id,
        action_type=action_type,
        action_payload_json=action_payload_json,
        status=status,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_action_by_id(
    db: AsyncSession,
    *,
    action_id: int,
) -> MentoringActionLog | None:
    result = await db.execute(
        select(MentoringActionLog).filter(MentoringActionLog.id == action_id)
    )
    return result.scalars().first()


async def list_actions_by_session(
    db: AsyncSession,
    *,
    session_id: int,
) -> list[MentoringActionLog]:
    result = await db.execute(
        select(MentoringActionLog)
        .filter(MentoringActionLog.session_id == session_id)
        .order_by(MentoringActionLog.created_at.desc(), MentoringActionLog.id.desc())
    )
    return list(result.scalars().all())
