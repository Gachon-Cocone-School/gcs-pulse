from __future__ import annotations

import json
import secrets
import hashlib
import string
from datetime import date, datetime

from app import crud_snippets
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


async def get_achievement_definitions_by_codes(
    db: AsyncSession,
    codes: Iterable[str],
) -> dict[str, AchievementDefinition]:
    normalized_codes = [code for code in dict.fromkeys(codes) if code]
    if not normalized_codes:
        return {}

    result = await db.execute(
        select(AchievementDefinition).filter(AchievementDefinition.code.in_(normalized_codes))
    )
    items = list(result.scalars().all())
    return {item.code: item for item in items}


async def upsert_achievement_definitions(
    db: AsyncSession,
    definitions: Iterable[dict],
    commit: bool = True,
) -> list[AchievementDefinition]:
    normalized_definitions: list[dict] = []
    seen_codes: set[str] = set()

    for item in definitions:
        raw_code = str(item.get("code") or "").strip()
        if not raw_code or raw_code in seen_codes:
            continue
        seen_codes.add(raw_code)
        normalized_definitions.append(
            {
                "code": raw_code,
                "name": str(item.get("name") or raw_code),
                "description": str(item.get("description") or raw_code),
                "badge_image_url": str(item.get("badge_image_url") or "https://example.com/achievements/default.png"),
                "rarity": str(item.get("rarity") or "common"),
                "is_public_announceable": bool(item.get("is_public_announceable", False)),
            }
        )

    if not normalized_definitions:
        return []

    codes = [item["code"] for item in normalized_definitions]
    existing_by_code = await get_achievement_definitions_by_codes(db, codes)

    rows: list[AchievementDefinition] = []
    for item in normalized_definitions:
        existing = existing_by_code.get(item["code"])
        if existing is None:
            row = AchievementDefinition(**item)
            db.add(row)
            rows.append(row)
            continue

        existing.name = item["name"]
        existing.description = item["description"]
        existing.badge_image_url = item["badge_image_url"]
        existing.rarity = item["rarity"]
        existing.is_public_announceable = item["is_public_announceable"]
        rows.append(existing)

    if commit:
        await db.commit()
    else:
        await db.flush()

    return rows


list_daily_snippets_for_date = crud_snippets.list_daily_snippets_for_date
list_daily_snippets_in_range = crud_snippets.list_daily_snippets_in_range
list_weekly_snippets_for_week = crud_snippets.list_weekly_snippets_for_week


async def list_achievement_grant_histories_for_rule_codes(
    db: AsyncSession,
    rule_codes: Iterable[str],
) -> list[tuple[str, int, str]]:
    normalized_codes = [code for code in dict.fromkeys(rule_codes) if code]
    if not normalized_codes:
        return []

    result = await db.execute(
        select(
            AchievementDefinition.code,
            AchievementGrant.user_id,
            AchievementGrant.external_grant_id,
        )
        .join(AchievementDefinition, AchievementGrant.achievement_definition_id == AchievementDefinition.id)
        .filter(
            AchievementDefinition.code.in_(normalized_codes),
            AchievementGrant.external_grant_id.is_not(None),
        )
        .order_by(AchievementGrant.id.asc())
    )
    return [(str(code), int(user_id), str(external_grant_id)) for code, user_id, external_grant_id in result.all()]


async def delete_achievement_grants_for_external_prefix(
    db: AsyncSession,
    prefix: str,
    commit: bool = True,
) -> int:
    if not prefix:
        return 0

    result = await db.execute(
        delete(AchievementGrant).filter(
            AchievementGrant.external_grant_id.is_not(None),
            AchievementGrant.external_grant_id.like(f"{prefix}%"),
        )
    )
    deleted_count = int(result.rowcount or 0)
    if commit:
        await db.commit()
    else:
        await db.flush()
    return deleted_count


async def bulk_create_achievement_grants(
    db: AsyncSession,
    grants: list[dict] | Iterable[AchievementGrant],
    commit: bool = True,
) -> list[AchievementGrant]:
    if not grants:
        return []

    rows: list[AchievementGrant] = []
    for grant in grants:
        if isinstance(grant, AchievementGrant):
            rows.append(grant)
        else:
            rows.append(AchievementGrant(**grant))

    db.add_all(rows)
    if commit:
        await db.commit()
    else:
        await db.flush()
    return rows


async def list_recent_public_achievement_grants(
    db: AsyncSession,
    now: datetime,
    limit: int,
) -> Tuple[list[dict], int]:
    rarity_rank = case(
        (AchievementDefinition.rarity == "legend", 5),
        (AchievementDefinition.rarity == "epic", 4),
        (AchievementDefinition.rarity == "rare", 3),
        (AchievementDefinition.rarity == "uncommon", 2),
        else_=1,
    )

    base_stmt = (
        select(AchievementGrant, AchievementDefinition, User)
        .join(AchievementDefinition, AchievementGrant.achievement_definition_id == AchievementDefinition.id)
        .join(User, AchievementGrant.user_id == User.id)
        .filter(
            AchievementDefinition.is_public_announceable == True,
            AchievementGrant.publish_start_at <= now,
            (AchievementGrant.publish_end_at.is_(None)) | (AchievementGrant.publish_end_at >= now),
        )
        .order_by(rarity_rank.desc(), AchievementGrant.granted_at.desc(), AchievementGrant.id.desc())
    )

    total = await _count(db, base_stmt)
    result = await db.execute(base_stmt.limit(limit))

    rows: list[dict] = []
    for grant, definition, user in result.all():
        rows.append(
            {
                "grant_id": grant.id,
                "user_id": user.id,
                "user_name": user.name or user.email,
                "achievement_definition_id": definition.id,
                "achievement_code": definition.code,
                "achievement_name": definition.name,
                "achievement_description": definition.description,
                "badge_image_url": definition.badge_image_url,
                "rarity": definition.rarity,
                "granted_at": grant.granted_at,
                "publish_start_at": grant.publish_start_at,
                "publish_end_at": grant.publish_end_at,
            }
        )

    return rows, total


async def list_my_achievement_groups(
    db: AsyncSession,
    user_id: int,
) -> list[dict]:
    rarity_rank = case(
        (AchievementDefinition.rarity == "legend", 5),
        (AchievementDefinition.rarity == "epic", 4),
        (AchievementDefinition.rarity == "rare", 3),
        (AchievementDefinition.rarity == "uncommon", 2),
        else_=1,
    )

    stmt = (
        select(
            AchievementGrant.achievement_definition_id,
            func.count(AchievementGrant.id).label("grant_count"),
            func.max(AchievementGrant.granted_at).label("last_granted_at"),
            AchievementDefinition.code,
            AchievementDefinition.name,
            AchievementDefinition.description,
            AchievementDefinition.badge_image_url,
            AchievementDefinition.rarity,
        )
        .join(AchievementDefinition, AchievementGrant.achievement_definition_id == AchievementDefinition.id)
        .filter(AchievementGrant.user_id == user_id)
        .group_by(
            AchievementGrant.achievement_definition_id,
            AchievementDefinition.code,
            AchievementDefinition.name,
            AchievementDefinition.description,
            AchievementDefinition.badge_image_url,
            AchievementDefinition.rarity,
        )
        .order_by(
            rarity_rank.desc(),
            func.max(AchievementGrant.granted_at).desc(),
            AchievementGrant.achievement_definition_id.desc(),
        )
    )

    result = await db.execute(stmt)

    rows: list[dict] = []
    for row in result.all():
        rows.append(
            {
                "achievement_definition_id": row.achievement_definition_id,
                "code": row.code,
                "name": row.name,
                "description": row.description,
                "badge_image_url": row.badge_image_url,
                "rarity": row.rarity,
                "grant_count": int(row.grant_count),
                "last_granted_at": row.last_granted_at,
            }
        )

    return rows


# -------------------------
# Comment CRUD
# -------------------------

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
    # load user relationship
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
