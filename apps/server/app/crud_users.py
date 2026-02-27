from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    normalized_email = email.strip().lower()
    result = await db.execute(
        select(User)
        .options(selectinload(User.consents))
        .filter(func.lower(User.email) == normalized_email)
    )
    return result.scalars().first()


async def get_user_by_email_basic(db: AsyncSession, email: str) -> Optional[User]:
    normalized_email = email.strip().lower()
    result = await db.execute(select(User).filter(func.lower(User.email) == normalized_email))
    return result.scalars().first()


async def create_or_update_user(db: AsyncSession, user_info: dict) -> User:
    user_email = str(user_info.get("email") or "").strip().lower()
    if not user_email:
        raise ValueError("email is required")

    user = await get_user_by_email(db, user_email)

    name: str = str(user_info.get("name") or "")
    picture: str = str(user_info.get("picture") or "")

    if not user:
        user = User(
            email=user_email,
            name=name,
            picture=picture,
        )
        db.add(user)
    else:
        user.email = user_email
        setattr(user, "name", name)
        setattr(user, "picture", picture)

    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def set_user_team(db: AsyncSession, user: User, team_id: Optional[int]) -> User:
    setattr(user, "team_id", team_id)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_league_type(db: AsyncSession, user: User, league_type: str) -> User:
    setattr(user, "league_type", league_type)
    await db.commit()
    await db.refresh(user)
    return user
