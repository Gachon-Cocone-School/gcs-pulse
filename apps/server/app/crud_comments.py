from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import cast, delete, or_
from sqlalchemy import Date as SADate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.crud_notifications import create_comment_notifications
from app.models import Comment, DailySnippet, Notification, User, UserTeamHistory, WeeklySnippet


logger = logging.getLogger(__name__)


async def create_comment(
    db: AsyncSession,
    user_id: int,
    content: str,
    daily_snippet_id: Optional[int] = None,
    weekly_snippet_id: Optional[int] = None,
    comment_type: str = "peer",
) -> Comment:
    new_comment = Comment(
        user_id=user_id,
        content=content,
        daily_snippet_id=daily_snippet_id,
        weekly_snippet_id=weekly_snippet_id,
        comment_type=comment_type,
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
    await db.execute(delete(Notification).where(Notification.comment_id == comment.id))
    await db.delete(comment)
    await db.commit()


async def get_mentionable_users_for_snippet(
    db: AsyncSession,
    daily_snippet_id: Optional[int] = None,
    weekly_snippet_id: Optional[int] = None,
) -> List[User]:
    """해당 스니펫에 접근 가능한 사용자 목록 반환 (팀원 + 교수/admin)."""
    snippet_date: Optional[date] = None
    owner_id: Optional[int] = None

    if daily_snippet_id is not None:
        result = await db.execute(
            select(DailySnippet).filter(DailySnippet.id == daily_snippet_id)
        )
        snippet = result.scalars().first()
        if not snippet:
            return []
        snippet_date = snippet.date
        owner_id = snippet.user_id
    elif weekly_snippet_id is not None:
        result = await db.execute(
            select(WeeklySnippet).filter(WeeklySnippet.id == weekly_snippet_id)
        )
        snippet = result.scalars().first()
        if not snippet:
            return []
        snippet_date = snippet.week
        owner_id = snippet.user_id
    else:
        return []

    team_member_ids: set[int] = set()

    # 스니펫 날짜 기준으로 같은 팀이었던 팀원 조회
    if snippet_date is not None and owner_id is not None:
        owner_team_result = await db.execute(
            select(UserTeamHistory.team_id).filter(
                UserTeamHistory.user_id == owner_id,
                cast(UserTeamHistory.joined_at, SADate) <= snippet_date,
                or_(
                    UserTeamHistory.left_at.is_(None),
                    cast(UserTeamHistory.left_at, SADate) >= snippet_date,
                ),
            ).limit(1)
        )
        owner_team_id = owner_team_result.scalar_one_or_none()

        if owner_team_id is not None:
            member_ids_result = await db.execute(
                select(UserTeamHistory.user_id).filter(
                    UserTeamHistory.team_id == owner_team_id,
                    cast(UserTeamHistory.joined_at, SADate) <= snippet_date,
                    or_(
                        UserTeamHistory.left_at.is_(None),
                        cast(UserTeamHistory.left_at, SADate) >= snippet_date,
                    ),
                )
            )
            team_member_ids = {int(uid) for uid in member_ids_result.scalars().all()}

    # 모든 이름 있는 사용자 로드 후, 팀원 또는 교수/admin을 Python에서 필터링
    # (JSON role 체크를 Python에서 수행하여 DB 독립성 확보)
    all_named_result = await db.execute(select(User).filter(User.name.is_not(None)))
    all_named = list(all_named_result.scalars().all())

    result_users: list[User] = []
    for u in all_named:
        roles = u.roles or []
        is_privileged = isinstance(roles, list) and ("교수" in roles or "admin" in roles)
        if u.id in team_member_ids or is_privileged:
            result_users.append(u)

    return result_users
