from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProfessorMentoringMemory

MAX_MEMORY_BYTES = 5120


def _truncate_to_max_bytes(value: str, max_bytes: int = MAX_MEMORY_BYTES) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value

    truncated = encoded[:max_bytes]
    return truncated.decode("utf-8", errors="ignore")


async def get_or_create_professor_memory(
    db: AsyncSession,
    *,
    professor_user_id: int,
) -> ProfessorMentoringMemory:
    result = await db.execute(
        select(ProfessorMentoringMemory).filter(
            ProfessorMentoringMemory.professor_user_id == professor_user_id
        )
    )
    row = result.scalars().first()
    if row is not None:
        return row

    row = ProfessorMentoringMemory(
        professor_user_id=professor_user_id,
        memory_markdown="",
        updated_by="system",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_professor_memory(
    db: AsyncSession,
    *,
    professor_user_id: int,
    memory_markdown: str,
    updated_by: str,
) -> ProfessorMentoringMemory:
    row = await get_or_create_professor_memory(db, professor_user_id=professor_user_id)
    row.memory_markdown = _truncate_to_max_bytes(memory_markdown)
    row.updated_by = updated_by
    await db.commit()
    await db.refresh(row)
    return row
