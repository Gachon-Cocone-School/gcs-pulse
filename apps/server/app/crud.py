from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import Consent, DailySnippet, Team, Term, User, WeeklySnippet
from app.schemas import ConsentCreate


async def _count(db: AsyncSession, stmt) -> int:
    subq = stmt.subquery()
    result = await db.execute(select(func.count()).select_from(subq))
    return int(result.scalar_one())


async def get_user_by_sub(db: AsyncSession, google_sub: str) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.consents))
        .filter(User.google_sub == google_sub)
    )
    return result.scalars().first()


async def create_or_update_user(db: AsyncSession, user_info: dict) -> User:
    user = await get_user_by_sub(db, user_info["sub"])

    name: str = str(user_info.get("name") or "")
    picture: str = str(user_info.get("picture") or "")

    if not user:
        user = User(
            google_sub=user_info["sub"],
            email=user_info["email"],
            name=name,
            picture=picture,
        )
        db.add(user)
    else:
        user.email = user_info["email"]
        setattr(user, "name", name)
        setattr(user, "picture", picture)

    await db.commit()
    await db.refresh(user)
    return user


async def get_active_terms(db: AsyncSession) -> List[Term]:
    result = await db.execute(select(Term).filter(Term.is_active == True))
    return list(result.scalars().all())


async def get_term_by_id(db: AsyncSession, term_id: int) -> Optional[Term]:
    result = await db.execute(select(Term).filter(Term.id == term_id))
    return result.scalars().first()


async def get_consent(
    db: AsyncSession, user_id: int, term_id: int
) -> Optional[Consent]:
    result = await db.execute(
        select(Consent).filter(Consent.user_id == user_id, Consent.term_id == term_id)
    )
    return result.scalars().first()


async def create_consent(db: AsyncSession, user_id: int, term_id: int) -> Consent:
    new_consent = Consent(user_id=user_id, term_id=term_id)
    db.add(new_consent)
    await db.commit()
    await db.refresh(new_consent)
    return new_consent



async def create_team(db: AsyncSession, name: str) -> Team:
    team = Team(name=name)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return await get_team_with_members(db, team.id)


async def list_teams(db: AsyncSession, limit: int = 100, offset: int = 0) -> Tuple[List[Team], int]:
    base = select(Team).options(selectinload(Team.members)).order_by(Team.id.desc())
    total = await _count(db, base)
    result = await db.execute(base.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def get_team_by_id(db: AsyncSession, team_id: int) -> Optional[Team]:
    result = await db.execute(select(Team).filter(Team.id == team_id))
    return result.scalars().first()


async def get_team_with_members(db: AsyncSession, team_id: int) -> Optional[Team]:
    result = await db.execute(
        select(Team).options(selectinload(Team.members)).filter(Team.id == team_id)
    )
    return result.scalars().first()


async def update_team(db: AsyncSession, team: Team, name: Optional[str]) -> Team:
    if name is not None:
        setattr(team, "name", name)
    await db.commit()
    await db.refresh(team)
    return await get_team_with_members(db, team.id)


async def delete_team(db: AsyncSession, team: Team) -> None:
    await db.delete(team)
    await db.commit()


async def set_user_team(db: AsyncSession, user: User, team_id: Optional[int]) -> User:
    setattr(user, "team_id", team_id)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def create_daily_snippet(
    db: AsyncSession,
    user_id: int,
    snippet_date: date,
    content: str,
    structured: Optional[str] = None,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> DailySnippet:
    snippet = DailySnippet(
        user_id=user_id,
        date=snippet_date,
        content=content,
        structured=structured,
        playbook=playbook,
        feedback=feedback,
    )
    db.add(snippet)
    await db.commit()
    await db.refresh(snippet)
    return snippet


async def upsert_daily_snippet(
    db: AsyncSession,
    user_id: int,
    snippet_date: date,
    content: str,
    structured: Optional[str] = None,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> DailySnippet:
    existing = await get_daily_snippet_by_user_and_date(db, user_id, snippet_date)
    if existing:
        return await update_daily_snippet(
            db, existing, content, structured=structured, playbook=playbook, feedback=feedback
        )
    return await create_daily_snippet(
        db, user_id, snippet_date, content, structured=structured, playbook=playbook, feedback=feedback
    )


async def get_daily_snippet_by_id(db: AsyncSession, snippet_id: int) -> Optional[DailySnippet]:
    result = await db.execute(select(DailySnippet).filter(DailySnippet.id == snippet_id))
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
    structured: Optional[str] = None,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> DailySnippet:
    setattr(snippet, "content", content)
    if structured is not None:
        setattr(snippet, "structured", structured)
    if playbook is not None:
        setattr(snippet, "playbook", playbook)
    if feedback is not None:
        setattr(snippet, "feedback", feedback)
    await db.commit()
    await db.refresh(snippet)
    return snippet


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
) -> Tuple[List[DailySnippet], int]:
    stmt = select(DailySnippet).join(User, DailySnippet.user_id == User.id)

    if viewer.team_id is None:
        stmt = stmt.filter(DailySnippet.user_id == viewer.id)
    else:
        stmt = stmt.filter((DailySnippet.user_id == viewer.id) | (User.team_id == viewer.team_id))

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
    return list(result.scalars().all()), total


async def create_weekly_snippet(
    db: AsyncSession,
    user_id: int,
    week: date,
    content: str,
    structured: Optional[str] = None,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> WeeklySnippet:
    snippet = WeeklySnippet(
        user_id=user_id,
        week=week,
        content=content,
        structured=structured,
        playbook=playbook,
        feedback=feedback,
    )
    db.add(snippet)
    await db.commit()
    await db.refresh(snippet)
    return snippet


async def upsert_weekly_snippet(
    db: AsyncSession,
    user_id: int,
    week: date,
    content: str,
    structured: Optional[str] = None,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> WeeklySnippet:
    existing = await get_weekly_snippet_by_user_and_week(db, user_id, week)
    if existing:
        return await update_weekly_snippet(
            db, existing, content, structured=structured, playbook=playbook, feedback=feedback
        )
    return await create_weekly_snippet(
        db, user_id, week, content, structured=structured, playbook=playbook, feedback=feedback
    )


async def get_weekly_snippet_by_id(db: AsyncSession, snippet_id: int) -> Optional[WeeklySnippet]:
    result = await db.execute(select(WeeklySnippet).filter(WeeklySnippet.id == snippet_id))
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
    structured: Optional[str] = None,
    playbook: Optional[str] = None,
    feedback: Optional[str] = None,
) -> WeeklySnippet:
    setattr(snippet, "content", content)
    if structured is not None:
        setattr(snippet, "structured", structured)
    if playbook is not None:
        setattr(snippet, "playbook", playbook)
    if feedback is not None:
        setattr(snippet, "feedback", feedback)
    await db.commit()
    await db.refresh(snippet)
    return snippet


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
) -> Tuple[List[WeeklySnippet], int]:
    stmt = select(WeeklySnippet).join(User, WeeklySnippet.user_id == User.id)

    if viewer.team_id is None:
        stmt = stmt.filter(WeeklySnippet.user_id == viewer.id)
    else:
        stmt = stmt.filter((WeeklySnippet.user_id == viewer.id) | (User.team_id == viewer.team_id))

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
