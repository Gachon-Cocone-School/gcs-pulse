from __future__ import annotations

import secrets
import string

from app import crud_achievements, crud_comments, crud_leaderboards, crud_snippets, crud_tokens
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import (
    Consent,
    Team,
    Term,
    User,
)


async def _count(db: AsyncSession, stmt) -> int:
    subq = stmt.subquery()
    result = await db.execute(select(func.count()).select_from(subq))
    return int(result.scalar_one())


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


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


create_daily_snippet = crud_snippets.create_daily_snippet
upsert_daily_snippet = crud_snippets.upsert_daily_snippet
get_daily_snippet_by_id = crud_snippets.get_daily_snippet_by_id
get_daily_snippet_by_user_and_date = crud_snippets.get_daily_snippet_by_user_and_date
update_daily_snippet = crud_snippets.update_daily_snippet
delete_daily_snippet = crud_snippets.delete_daily_snippet
list_daily_snippets = crud_snippets.list_daily_snippets


create_api_token = crud_tokens.create_api_token
list_api_tokens = crud_tokens.list_api_tokens
get_api_token_by_raw_token = crud_tokens.get_api_token_by_raw_token
touch_api_token_last_used_at = crud_tokens.touch_api_token_last_used_at
delete_api_token = crud_tokens.delete_api_token


create_weekly_snippet = crud_snippets.create_weekly_snippet
upsert_weekly_snippet = crud_snippets.upsert_weekly_snippet
get_weekly_snippet_by_id = crud_snippets.get_weekly_snippet_by_id
get_weekly_snippet_by_user_and_week = crud_snippets.get_weekly_snippet_by_user_and_week
update_weekly_snippet = crud_snippets.update_weekly_snippet
delete_weekly_snippet = crud_snippets.delete_weekly_snippet


_parse_total_score = crud_leaderboards._parse_total_score
apply_competition_ranks = crud_leaderboards.apply_competition_ranks
build_individual_leaderboard = crud_leaderboards.build_individual_leaderboard
build_team_leaderboard = crud_leaderboards.build_team_leaderboard


list_weekly_snippets = crud_snippets.list_weekly_snippets


get_achievement_definitions_by_codes = crud_achievements.get_achievement_definitions_by_codes
upsert_achievement_definitions = crud_achievements.upsert_achievement_definitions


list_daily_snippets_for_date = crud_snippets.list_daily_snippets_for_date
list_daily_snippets_in_range = crud_snippets.list_daily_snippets_in_range
list_weekly_snippets_for_week = crud_snippets.list_weekly_snippets_for_week


list_achievement_grant_histories_for_rule_codes = crud_achievements.list_achievement_grant_histories_for_rule_codes
delete_achievement_grants_for_external_prefix = crud_achievements.delete_achievement_grants_for_external_prefix
bulk_create_achievement_grants = crud_achievements.bulk_create_achievement_grants
list_recent_public_achievement_grants = crud_achievements.list_recent_public_achievement_grants
list_my_achievement_groups = crud_achievements.list_my_achievement_groups


# -------------------------
# Comment CRUD
# -------------------------

create_comment = crud_comments.create_comment
list_comments = crud_comments.list_comments
get_comment_by_id = crud_comments.get_comment_by_id
update_comment = crud_comments.update_comment
delete_comment = crud_comments.delete_comment
