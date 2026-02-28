from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import RoleAssignmentRule, User


def _match_email_pattern(pattern: str, normalized_email: str) -> bool:
    regex_parts: list[str] = []
    for char in pattern:
        if char == "%":
            regex_parts.append(".*")
            continue
        if char == "_":
            regex_parts.append(".")
            continue
        regex_parts.append(re.escape(char))

    regex_pattern = "^" + "".join(regex_parts) + "$"
    return re.match(regex_pattern, normalized_email) is not None


def _rule_matches_email(rule: RoleAssignmentRule, normalized_email: str) -> bool:
    if not isinstance(rule.rule_value, dict):
        return False

    if rule.rule_type == "email_list":
        emails = rule.rule_value.get("emails")
        if not isinstance(emails, list):
            return False
        normalized_emails = {
            str(email).strip().lower() for email in emails if str(email).strip()
        }
        return normalized_email in normalized_emails

    if rule.rule_type == "email_pattern":
        pattern = str(rule.rule_value.get("pattern") or "").strip().lower()
        if not pattern:
            return False
        return _match_email_pattern(pattern, normalized_email)

    return False


def _resolve_roles_from_rules(
    normalized_email: str, rules: list[RoleAssignmentRule]
) -> list[str]:
    assigned_roles: list[str] = []

    for rule in rules:
        assigned_role = str(rule.assigned_role or "").strip()
        if not assigned_role:
            continue
        if _rule_matches_email(rule, normalized_email) and assigned_role not in assigned_roles:
            assigned_roles.append(assigned_role)

    return assigned_roles or ["user"]


async def _resolve_roles_for_email(db: AsyncSession, normalized_email: str) -> list[str]:
    result = await db.execute(
        select(RoleAssignmentRule)
        .filter(RoleAssignmentRule.is_active.is_(True))
        .order_by(RoleAssignmentRule.priority.asc(), RoleAssignmentRule.id.asc())
    )
    rules = result.scalars().all()
    return _resolve_roles_from_rules(normalized_email, rules)


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

    resolved_roles = await _resolve_roles_for_email(db, user_email)

    if not user:
        user = User(
            email=user_email,
            name=name,
            picture=picture,
            roles=resolved_roles,
        )
        db.add(user)
    else:
        user.email = user_email
        setattr(user, "name", name)
        setattr(user, "picture", picture)
        setattr(user, "roles", resolved_roles)

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
