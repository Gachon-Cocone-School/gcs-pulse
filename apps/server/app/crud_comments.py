from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.crud_notifications import create_comment_notifications
from app.models import Comment


logger = logging.getLogger(__name__)


async def create_comment(
    db: AsyncSession,
    user_id: int,
    content: str,
    daily_snippet_id: Optional[int] = None,
    weekly_snippet_id: Optional[int] = None,
) -> Comment:
    new_comment = Comment(
        user_id=user_id,
        content=content,
        daily_snippet_id=daily_snippet_id,
        weekly_snippet_id=weekly_snippet_id,
    )
    db.add(new_comment)
    await db.commit()

    try:
        await create_comment_notifications(db, comment=new_comment)
    except Exception:
        logger.exception("Failed to create notifications after comment creation")

    return await get_comment_by_id(db, new_comment.id)


async def list_comments(
    db: AsyncSession,
    daily_snippet_id: Optional[int] = None,
    weekly_snippet_id: Optional[int] = None,
) -> List[Comment]:
    stmt = select(Comment).options(selectinload(Comment.user)).order_by(Comment.created_at.asc())
    if daily_snippet_id is not None:
        stmt = stmt.filter(Comment.daily_snippet_id == daily_snippet_id)
    elif weekly_snippet_id is not None:
        stmt = stmt.filter(Comment.weekly_snippet_id == weekly_snippet_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_comment_by_id(db: AsyncSession, comment_id: int) -> Optional[Comment]:
    result = await db.execute(
        select(Comment).options(selectinload(Comment.user)).filter(Comment.id == comment_id)
    )
    return result.scalars().first()


async def update_comment(db: AsyncSession, comment: Comment, content: str) -> Comment:
    setattr(comment, "content", content)
    await db.commit()
    return await get_comment_by_id(db, comment.id)


async def delete_comment(db: AsyncSession, comment: Comment) -> None:
    await db.delete(comment)
    await db.commit()
