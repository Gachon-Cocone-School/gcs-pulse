from __future__ import annotations

import json
import secrets
import hashlib
import string
from datetime import date, datetime
from typing import List, Optional, Tuple

from sqlalchemy import case, func
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


async def get_user_by_sub(db: AsyncSession, google_sub: str) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.consents))
        .filter(User.google_sub == google_sub)
    )
    return result.scalars().first()


async def get_user_by_sub_basic(db: AsyncSession, google_sub: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.google_sub == google_sub))
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
    return await get_daily_snippet_by_id(db, snippet.id)


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
    # Build base statement for snippets
    stmt = select(DailySnippet).join(User, DailySnippet.user_id == User.id).options(selectinload(DailySnippet.user))

    if scope == "team":
        if viewer.team_id is None:
             return [], 0
        stmt = stmt.filter(User.team_id == viewer.team_id)
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

    # Count total
    total = await _count(db, stmt)

    # Execute main query for items
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = list(result.scalars().all())

    # For each snippet, compute comments_count using a fast count query
    # Collect snippet IDs
    snippet_ids = [s.id for s in items]
    if snippet_ids:
        count_stmt = select(Comment.daily_snippet_id, func.count()).where(Comment.daily_snippet_id.in_(snippet_ids)).group_by(Comment.daily_snippet_id)
        counts = await db.execute(count_stmt)
        count_map = {row[0]: row[1] for row in counts.fetchall()}
    else:
        count_map = {}

    # Attach comments_count attribute to each snippet object
    for s in items:
        setattr(s, "comments_count", int(count_map.get(s.id, 0)))

    return items, total


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
    return await get_weekly_snippet_by_id(db, snippet.id)


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
    return await get_weekly_snippet_by_id(db, snippet.id)


async def delete_weekly_snippet(db: AsyncSession, snippet: WeeklySnippet) -> None:
    await db.delete(snippet)
    await db.commit()


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

    if scope == "team":
        if viewer.team_id is None:
            return [], 0
        stmt = stmt.filter(User.team_id == viewer.team_id)
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
