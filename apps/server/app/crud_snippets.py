from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List

from sqlalchemy import Date as SADate, and_, cast, false, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.dependencies import has_snippet_full_read_role, has_snippet_team_read_role
from app.models import Comment, DailySnippet, User, UserTeamHistory, WeeklySnippet


async def _count(db: AsyncSession, stmt) -> int:
    subq = stmt.subquery()
    result = await db.execute(select(func.count()).select_from(subq))
    return int(result.scalar_one())


async def create_daily_snippet(
    db: AsyncSession,
    user_id: int,
    snippet_date: date,
    content: str,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> DailySnippet:
    snippet = DailySnippet(
        user_id=user_id,
        date=snippet_date,
        content=content,
        playbook=playbook,
        feedback=feedback,
    )
    db.add(snippet)
    await db.commit()
    await db.refresh(snippet)
    return await get_daily_snippet_by_id(db, snippet.id)


async def upsert_daily_snippet(
    db: AsyncSession,
    user_id: int,
    snippet_date: date,
    content: str,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> DailySnippet:
    existing = await get_daily_snippet_by_user_and_date(db, user_id, snippet_date)
    if existing:
        return await update_daily_snippet(
            db, existing, content, playbook=playbook, feedback=feedback
        )
    return await create_daily_snippet(
        db, user_id, snippet_date, content, playbook=playbook, feedback=feedback
    )


async def get_daily_snippet_by_id(db: AsyncSession, snippet_id: int) -> Optional[DailySnippet]:
    result = await db.execute(
        select(DailySnippet)
        .options(selectinload(DailySnippet.user))
        .filter(DailySnippet.id == snippet_id)
    )
    return result.scalars().first()


async def get_daily_snippet_by_user_and_date(
    db: AsyncSession, user_id: int, snippet_date: date
) -> Optional[DailySnippet]:
    result = await db.execute(
        select(DailySnippet).filter(DailySnippet.user_id == user_id, DailySnippet.date == snippet_date)
    )
    return result.scalars().first()


async def update_daily_snippet(
    db: AsyncSession,
    snippet: DailySnippet,
    content: str,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> DailySnippet:
    setattr(snippet, "content", content)
    if playbook is not None:
        setattr(snippet, "playbook", playbook)
    if feedback is not None:
        setattr(snippet, "feedback", feedback)
    await db.commit()
    await db.refresh(snippet)
    return await get_daily_snippet_by_id(db, snippet.id)


async def delete_daily_snippet(db: AsyncSession, snippet: DailySnippet) -> None:
    await db.delete(snippet)
    await db.commit()


async def list_daily_snippets(
    db: AsyncSession,
    viewer: User,
    limit: int,
    offset: int,
    order: str,
    from_date: Optional[date],
    to_date: Optional[date],
    q: Optional[str],
    scope: str = "own",
) -> Tuple[List[DailySnippet], int]:
    stmt = select(DailySnippet).join(User, DailySnippet.user_id == User.id).options(selectinload(DailySnippet.user))

    full_read = has_snippet_full_read_role(viewer)
    team_read = has_snippet_team_read_role(viewer)

    if not full_read and not team_read:
        stmt = stmt.filter(false())
    elif scope == "team":
        if full_read:
            pass
        else:
            vth = aliased(UserTeamHistory)
            oth = aliased(UserTeamHistory)
            team_overlap = (
                select(literal(1))
                .select_from(vth)
                .join(oth, vth.team_id == oth.team_id)
                .where(
                    and_(
                        vth.user_id == viewer.id,
                        oth.user_id == DailySnippet.user_id,
                        cast(vth.joined_at, SADate) <= DailySnippet.date,
                        or_(vth.left_at.is_(None), cast(vth.left_at, SADate) >= DailySnippet.date),
                        cast(oth.joined_at, SADate) <= DailySnippet.date,
                        or_(oth.left_at.is_(None), cast(oth.left_at, SADate) >= DailySnippet.date),
                    )
                )
                .correlate(DailySnippet)
                .exists()
            )
            stmt = stmt.filter(or_(DailySnippet.user_id == viewer.id, team_overlap))
    else:
        stmt = stmt.filter(DailySnippet.user_id == viewer.id)

    if from_date is not None:
        stmt = stmt.filter(DailySnippet.date >= from_date)
    if to_date is not None:
        stmt = stmt.filter(DailySnippet.date <= to_date)
    if q:
        stmt = stmt.filter(DailySnippet.content.ilike(f"%{q}%"))

    if order.lower() == "asc":
        stmt = stmt.order_by(DailySnippet.date.asc(), DailySnippet.id.asc())
    else:
        stmt = stmt.order_by(DailySnippet.date.desc(), DailySnippet.id.desc())

    total = await _count(db, stmt)

    result = await db.execute(stmt.limit(limit).offset(offset))
    items = list(result.scalars().all())

    snippet_ids = [s.id for s in items]
    if snippet_ids:
        count_stmt = select(Comment.daily_snippet_id, func.count()).where(Comment.daily_snippet_id.in_(snippet_ids)).group_by(Comment.daily_snippet_id)
        counts = await db.execute(count_stmt)
        count_map = {row[0]: row[1] for row in counts.fetchall()}
    else:
        count_map = {}

    for s in items:
        setattr(s, "comments_count", int(count_map.get(s.id, 0)))

    return items, total


async def create_weekly_snippet(
    db: AsyncSession,
    user_id: int,
    week: date,
    content: str,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> WeeklySnippet:
    snippet = WeeklySnippet(
        user_id=user_id,
        week=week,
        content=content,
        playbook=playbook,
        feedback=feedback,
    )
    db.add(snippet)
    await db.commit()
    await db.refresh(snippet)
    return await get_weekly_snippet_by_id(db, snippet.id)


async def upsert_weekly_snippet(
    db: AsyncSession,
    user_id: int,
    week: date,
    content: str,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> WeeklySnippet:
    existing = await get_weekly_snippet_by_user_and_week(db, user_id, week)
    if existing:
        return await update_weekly_snippet(
            db, existing, content, playbook=playbook, feedback=feedback
        )
    return await create_weekly_snippet(
        db, user_id, week, content, playbook=playbook, feedback=feedback
    )


async def get_weekly_snippet_by_id(db: AsyncSession, snippet_id: int) -> Optional[WeeklySnippet]:
    result = await db.execute(
        select(WeeklySnippet)
        .options(selectinload(WeeklySnippet.user))
        .filter(WeeklySnippet.id == snippet_id)
    )
    return result.scalars().first()


async def get_weekly_snippet_by_user_and_week(
    db: AsyncSession, user_id: int, week: date
) -> Optional[WeeklySnippet]:
    result = await db.execute(
        select(WeeklySnippet).filter(WeeklySnippet.user_id == user_id, WeeklySnippet.week == week)
    )
    return result.scalars().first()


async def update_weekly_snippet(
    db: AsyncSession,
    snippet: WeeklySnippet,
    content: str,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> WeeklySnippet:
    setattr(snippet, "content", content)
    if playbook is not None:
        setattr(snippet, "playbook", playbook)
    if feedback is not None:
        setattr(snippet, "feedback", feedback)
    await db.commit()
    await db.refresh(snippet)
    return await get_weekly_snippet_by_id(db, snippet.id)


async def delete_weekly_snippet(db: AsyncSession, snippet: WeeklySnippet) -> None:
    await db.delete(snippet)
    await db.commit()


async def list_weekly_snippets(
    db: AsyncSession,
    viewer: User,
    limit: int,
    offset: int,
    order: str,
    from_week: Optional[date],
    to_week: Optional[date],
    q: Optional[str],
    scope: str = "own",
) -> Tuple[List[WeeklySnippet], int]:
    stmt = select(WeeklySnippet).join(User, WeeklySnippet.user_id == User.id).options(selectinload(WeeklySnippet.user))

    full_read = has_snippet_full_read_role(viewer)
    team_read = has_snippet_team_read_role(viewer)

    if not full_read and not team_read:
        stmt = stmt.filter(false())
    elif scope == "team":
        if full_read:
            pass
        else:
            vth = aliased(UserTeamHistory)
            oth = aliased(UserTeamHistory)
            team_overlap = (
                select(literal(1))
                .select_from(vth)
                .join(oth, vth.team_id == oth.team_id)
                .where(
                    and_(
                        vth.user_id == viewer.id,
                        oth.user_id == WeeklySnippet.user_id,
                        cast(vth.joined_at, SADate) <= WeeklySnippet.week,
                        or_(vth.left_at.is_(None), cast(vth.left_at, SADate) >= WeeklySnippet.week),
                        cast(oth.joined_at, SADate) <= WeeklySnippet.week,
                        or_(oth.left_at.is_(None), cast(oth.left_at, SADate) >= WeeklySnippet.week),
                    )
                )
                .correlate(WeeklySnippet)
                .exists()
            )
            stmt = stmt.filter(or_(WeeklySnippet.user_id == viewer.id, team_overlap))
    else:
        stmt = stmt.filter(WeeklySnippet.user_id == viewer.id)

    if from_week is not None:
        stmt = stmt.filter(WeeklySnippet.week >= from_week)
    if to_week is not None:
        stmt = stmt.filter(WeeklySnippet.week <= to_week)
    if q:
        stmt = stmt.filter(WeeklySnippet.content.ilike(f"%{q}%"))

    if order.lower() == "asc":
        stmt = stmt.order_by(WeeklySnippet.week.asc(), WeeklySnippet.id.asc())
    else:
        stmt = stmt.order_by(WeeklySnippet.week.desc(), WeeklySnippet.id.desc())

    total = await _count(db, stmt)
    result = await db.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def list_daily_snippets_for_date(
    db: AsyncSession,
    target_date: date,
) -> list[DailySnippet]:
    result = await db.execute(
        select(DailySnippet)
        .filter(DailySnippet.date == target_date)
        .order_by(DailySnippet.user_id.asc(), DailySnippet.id.asc())
    )
    return list(result.scalars().all())


async def list_daily_snippets_in_range(
    db: AsyncSession,
    start_date: date,
    end_date: date,
) -> list[DailySnippet]:
    result = await db.execute(
        select(DailySnippet)
        .filter(DailySnippet.date >= start_date, DailySnippet.date <= end_date)
        .order_by(DailySnippet.date.asc(), DailySnippet.user_id.asc(), DailySnippet.id.asc())
    )
    return list(result.scalars().all())


async def list_weekly_snippets_for_week(
    db: AsyncSession,
    target_week: date,
) -> list[WeeklySnippet]:
    result = await db.execute(
        select(WeeklySnippet)
        .filter(WeeklySnippet.week == target_week)
        .order_by(WeeklySnippet.user_id.asc(), WeeklySnippet.id.asc())
    )
    return list(result.scalars().all())


async def list_daily_snippets_for_student(
    db: AsyncSession,
    *,
    student_user_id: int,
    limit: int,
    offset: int,
    order: str,
    from_date: Optional[date],
    to_date: Optional[date],
) -> Tuple[List[DailySnippet], int]:
    stmt = (
        select(DailySnippet)
        .join(User, DailySnippet.user_id == User.id)
        .options(selectinload(DailySnippet.user))
        .filter(DailySnippet.user_id == student_user_id)
    )

    if from_date is not None:
        stmt = stmt.filter(DailySnippet.date >= from_date)
    if to_date is not None:
        stmt = stmt.filter(DailySnippet.date <= to_date)

    if order.lower() == "asc":
        stmt = stmt.order_by(DailySnippet.date.asc(), DailySnippet.id.asc())
    else:
        stmt = stmt.order_by(DailySnippet.date.desc(), DailySnippet.id.desc())

    total = await _count(db, stmt)
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = list(result.scalars().all())

    snippet_ids = [s.id for s in items]
    if snippet_ids:
        count_stmt = (
            select(Comment.daily_snippet_id, func.count())
            .where(Comment.daily_snippet_id.in_(snippet_ids))
            .group_by(Comment.daily_snippet_id)
        )
        counts = await db.execute(count_stmt)
        count_map = {row[0]: row[1] for row in counts.fetchall()}
    else:
        count_map = {}

    for s in items:
        setattr(s, "comments_count", int(count_map.get(s.id, 0)))

    return items, total


async def list_weekly_snippets_for_student(
    db: AsyncSession,
    *,
    student_user_id: int,
    limit: int,
    offset: int,
    order: str,
    from_week: Optional[date],
    to_week: Optional[date],
) -> Tuple[List[WeeklySnippet], int]:
    stmt = (
        select(WeeklySnippet)
        .join(User, WeeklySnippet.user_id == User.id)
        .options(selectinload(WeeklySnippet.user))
        .filter(WeeklySnippet.user_id == student_user_id)
    )

    if from_week is not None:
        stmt = stmt.filter(WeeklySnippet.week >= from_week)
    if to_week is not None:
        stmt = stmt.filter(WeeklySnippet.week <= to_week)

    if order.lower() == "asc":
        stmt = stmt.order_by(WeeklySnippet.week.asc(), WeeklySnippet.id.asc())
    else:
        stmt = stmt.order_by(WeeklySnippet.week.desc(), WeeklySnippet.id.desc())

    total = await _count(db, stmt)
    result = await db.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all()), total
