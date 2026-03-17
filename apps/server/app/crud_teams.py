from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import Team, User, UserTeamHistory


async def _count(db: AsyncSession, stmt) -> int:
    subq = stmt.subquery()
    result = await db.execute(select(func.count()).select_from(subq))
    return int(result.scalar_one())


def generate_invite_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def create_team(
    db: AsyncSession,
    name: str,
    invite_code: Optional[str] = None,
    commit: bool = True,
) -> Team:
    code = (invite_code or generate_invite_code()).strip().upper()
    team = Team(name=name, invite_code=code)
    db.add(team)

    if commit:
        await db.commit()
    else:
        await db.flush()

    await db.refresh(team)

    if commit:
        return await get_team_with_members(db, team.id)
    return team


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


async def get_team_by_invite_code(db: AsyncSession, invite_code: str) -> Optional[Team]:
    normalized = invite_code.strip().upper()
    result = await db.execute(select(Team).filter(Team.invite_code == normalized))
    return result.scalars().first()


async def count_team_members(db: AsyncSession, team_id: int) -> int:
    result = await db.execute(select(func.count()).select_from(User).filter(User.team_id == team_id))
    return int(result.scalar_one())


async def update_team(
    db: AsyncSession,
    team: Team,
    name: Optional[str] = None,
    league_type: Optional[str] = None,
) -> Team:
    if name is not None:
        setattr(team, "name", name)
    if league_type is not None:
        setattr(team, "league_type", league_type)
    await db.commit()
    await db.refresh(team)
    return await get_team_with_members(db, team.id)


async def delete_team(db: AsyncSession, team: Team) -> None:
    await db.delete(team)
    await db.commit()


async def record_team_join(db: AsyncSession, user_id: int, team_id: int, joined_at: datetime) -> None:
    history = UserTeamHistory(user_id=user_id, team_id=team_id, joined_at=joined_at)
    db.add(history)


async def record_team_leave(db: AsyncSession, user_id: int, team_id: int, left_at: datetime) -> None:
    result = await db.execute(
        select(UserTeamHistory)
        .filter(
            UserTeamHistory.user_id == user_id,
            UserTeamHistory.team_id == team_id,
            UserTeamHistory.left_at.is_(None),
        )
        .order_by(UserTeamHistory.joined_at.desc())
        .limit(1)
    )
    history = result.scalars().first()
    if history:
        history.left_at = left_at
