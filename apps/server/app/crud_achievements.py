from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Tuple

from sqlalchemy import case, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import AchievementDefinition, AchievementGrant, User


async def _count(db: AsyncSession, stmt) -> int:
    subq = stmt.subquery()
    result = await db.execute(select(func.count()).select_from(subq))
    return int(result.scalar_one())


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
        if existing is not None:
            continue

        row = AchievementDefinition(**item)
        db.add(row)
        rows.append(row)

    if commit:
        await db.commit()
    else:
        await db.flush()

    return rows


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
