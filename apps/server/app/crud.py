from __future__ import annotations

import json
import secrets
import hashlib
import string
from datetime import date, datetime

from app import crud_achievements, crud_comments, crud_snippets
from typing import Iterable, List, Optional, Tuple

from sqlalchemy import case, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import (
    Consent,
    DailySnippet,
    Team,
    Term,
    User,
    WeeklySnippet,
    ApiToken,
    Comment,
    AchievementGrant,
    AchievementDefinition,
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


async def create_api_token(
    db: AsyncSession, user_id: int, description: str, idempotency_key: Optional[str] = None
) -> Tuple[ApiToken, str]:
    # If idempotency_key provided, check for an existing token for this user
    if idempotency_key:
        result = await db.execute(
            select(ApiToken).filter(ApiToken.user_id == user_id, ApiToken.idempotency_key == idempotency_key)
        )
        existing = result.scalars().first()
        if existing:
            # Return existing token without revealing raw token again
            return existing, ""

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    db_token = ApiToken(
        user_id=user_id,
        token_hash=token_hash,
        description=description,
        idempotency_key=idempotency_key,
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token, raw_token


async def list_api_tokens(db: AsyncSession, user_id: int) -> List[ApiToken]:
    result = await db.execute(
        select(ApiToken).filter(ApiToken.user_id == user_id).order_by(ApiToken.created_at.desc())
    )
    return list(result.scalars().all())


async def get_api_token_by_raw_token(db: AsyncSession, raw_token: str) -> Optional[ApiToken]:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await db.execute(select(ApiToken).filter(ApiToken.token_hash == token_hash))
    return result.scalars().first()


async def touch_api_token_last_used_at(
    db: AsyncSession, token: ApiToken, used_at: Optional[datetime] = None
) -> ApiToken:
    setattr(token, "last_used_at", used_at or datetime.now().astimezone())
    await db.commit()
    await db.refresh(token)
    return token


async def delete_api_token(db: AsyncSession, token_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(ApiToken).filter(ApiToken.id == token_id, ApiToken.user_id == user_id)
    )
    token = result.scalars().first()
    if token:
        await db.delete(token)
        await db.commit()
        return True
    return False


create_weekly_snippet = crud_snippets.create_weekly_snippet
upsert_weekly_snippet = crud_snippets.upsert_weekly_snippet
get_weekly_snippet_by_id = crud_snippets.get_weekly_snippet_by_id
get_weekly_snippet_by_user_and_week = crud_snippets.get_weekly_snippet_by_user_and_week
update_weekly_snippet = crud_snippets.update_weekly_snippet
delete_weekly_snippet = crud_snippets.delete_weekly_snippet


def _parse_total_score(feedback: Optional[str]) -> float:
    if not feedback:
        return 0.0
    try:
        parsed = json.loads(feedback)
    except (TypeError, ValueError, json.JSONDecodeError):
        return 0.0

    raw_score = parsed.get("total_score")
    if raw_score is None:
        return 0.0

    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return 0.0


def apply_competition_ranks(items: list[dict]) -> list[dict]:
    ranked_items = sorted(items, key=lambda item: (-item["score"], item["participant_name"], item["participant_id"]))
    previous_score: Optional[float] = None
    previous_rank = 0
    for index, item in enumerate(ranked_items, start=1):
        if previous_score is not None and item["score"] == previous_score:
            item["rank"] = previous_rank
        else:
            item["rank"] = index
            previous_rank = index
            previous_score = item["score"]
    return ranked_items


async def build_individual_leaderboard(
    db: AsyncSession,
    league_type: str,
    period: str,
    target_key: date,
) -> list[dict]:
    result = await db.execute(
        select(User)
        .filter(User.team_id.is_(None), User.league_type == league_type)
        .order_by(User.id.asc())
    )
    users = list(result.scalars().all())

    if not users:
        return []

    user_ids = [user.id for user in users]

    snippet_map: dict[int, float] = {}
    if period == "daily":
        snippet_result = await db.execute(
            select(DailySnippet)
            .filter(DailySnippet.user_id.in_(user_ids), DailySnippet.date == target_key)
        )
        for snippet in snippet_result.scalars().all():
            snippet_map[snippet.user_id] = _parse_total_score(snippet.feedback)
    else:
        snippet_result = await db.execute(
            select(WeeklySnippet)
            .filter(WeeklySnippet.user_id.in_(user_ids), WeeklySnippet.week == target_key)
        )
        for snippet in snippet_result.scalars().all():
            snippet_map[snippet.user_id] = _parse_total_score(snippet.feedback)

    items: list[dict] = []
    for user in users:
        items.append(
            {
                "rank": 0,
                "score": float(snippet_map.get(user.id, 0.0)),
                "participant_type": "individual",
                "participant_id": user.id,
                "participant_name": user.name or user.email,
            }
        )

    return apply_competition_ranks(items)


async def build_team_leaderboard(
    db: AsyncSession,
    league_type: str,
    period: str,
    target_key: date,
) -> list[dict]:
    teams_result = await db.execute(
        select(Team)
        .options(selectinload(Team.members))
        .filter(Team.league_type == league_type)
        .order_by(Team.id.asc())
    )
    teams = list(teams_result.scalars().all())

    if not teams:
        return []

    all_member_ids: list[int] = []
    for team in teams:
        all_member_ids.extend(member.id for member in team.members)

    score_map: dict[int, float] = {}
    submitted_member_ids: set[int] = set()
    if all_member_ids:
        if period == "daily":
            snippet_result = await db.execute(
                select(DailySnippet)
                .filter(DailySnippet.user_id.in_(all_member_ids), DailySnippet.date == target_key)
            )
            snippets = list(snippet_result.scalars().all())
        else:
            snippet_result = await db.execute(
                select(WeeklySnippet)
                .filter(WeeklySnippet.user_id.in_(all_member_ids), WeeklySnippet.week == target_key)
            )
            snippets = list(snippet_result.scalars().all())

        for snippet in snippets:
            score_map[snippet.user_id] = _parse_total_score(snippet.feedback)
            submitted_member_ids.add(snippet.user_id)

    items: list[dict] = []
    for team in teams:
        members = list(team.members)
        member_count = len(members)
        if member_count == 0:
            average_score = 0.0
            submitted_count = 0
        else:
            total_score = 0.0
            submitted_count = 0
            for member in members:
                total_score += float(score_map.get(member.id, 0.0))
                if member.id in submitted_member_ids:
                    submitted_count += 1
            average_score = total_score / member_count

        items.append(
            {
                "rank": 0,
                "score": float(average_score),
                "participant_type": "team",
                "participant_id": team.id,
                "participant_name": team.name,
                "member_count": member_count,
                "submitted_count": submitted_count,
            }
        )

    return apply_competition_ranks(items)


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
