from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import re
from typing import Optional, Tuple

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.lib.notification_runtime import registry as notification_registry
from app.models import (
    Comment,
    DailySnippet,
    Notification,
    NotificationSetting,
    User,
    WeeklySnippet,
)


MENTION_PATTERN = re.compile(r"@([^\s@]+)")


async def _count(db: AsyncSession, stmt) -> int:
    subq = stmt.subquery()
    result = await db.execute(select(func.count()).select_from(subq))
    return int(result.scalar_one())


def _extract_mention_tokens(content: str) -> set[str]:
    return {
        match.group(1).strip()
        for match in MENTION_PATTERN.finditer(content)
        if match.group(1).strip()
    }


def _split_name_and_department(value: str) -> tuple[str, str | None]:
    normalized = value.strip()
    if not normalized:
        return "", None

    if "/" not in normalized:
        return normalized, None

    raw_name, raw_department = normalized.split("/", 1)
    name = raw_name.strip()
    department = raw_department.strip()
    if not name:
        return "", None
    if not department:
        return name, None
    return name, department


def _matches_mention_token(user: User, mention_token: str) -> bool:
    mention_name, mention_department = _split_name_and_department(mention_token)
    if not mention_name:
        return False

    user_name = str(user.name or "").strip()
    if not user_name:
        return False

    if mention_department is None:
        return user_name == mention_name

    exact_token = f"{mention_name}/{mention_department}"
    if user_name == exact_token:
        return True

    user_name_only, user_department_from_name = _split_name_and_department(user_name)
    if (
        user_department_from_name is not None
        and user_name_only == mention_name
        and user_department_from_name == mention_department
    ):
        return True

    for department_attr in ("department", "major", "dept"):
        raw_department = getattr(user, department_attr, None)
        if raw_department is None:
            continue
        if user_name == mention_name and str(raw_department).strip() == mention_department:
            return True

    return False


async def _get_actor_team_id(db: AsyncSession, actor_user_id: int) -> int | None:
    result = await db.execute(select(User.team_id).filter(User.id == actor_user_id))
    return result.scalar_one_or_none()


async def _get_snippet_author_user_id(db: AsyncSession, comment: Comment) -> int | None:
    if comment.daily_snippet_id is not None:
        result = await db.execute(
            select(DailySnippet.user_id).filter(DailySnippet.id == comment.daily_snippet_id)
        )
        author_user_id = result.scalar_one_or_none()
        return int(author_user_id) if author_user_id is not None else None

    if comment.weekly_snippet_id is not None:
        result = await db.execute(
            select(WeeklySnippet.user_id).filter(WeeklySnippet.id == comment.weekly_snippet_id)
        )
        author_user_id = result.scalar_one_or_none()
        return int(author_user_id) if author_user_id is not None else None

    return None


async def _build_mention_user_ids(
    db: AsyncSession,
    mention_tokens: set[str],
    team_id: int | None,
) -> set[int]:
    if not mention_tokens:
        return set()

    conditions = []
    if team_id is not None:
        conditions.append(User.team_id == team_id)
    # 교수/admin은 팀 무관하게 모든 스니펫에 접근 가능하므로 멘션 후보에 포함
    conditions.append(User.roles.contains(["교수"]))
    conditions.append(User.roles.contains(["admin"]))

    result = await db.execute(
        select(User).filter(
            or_(*conditions),
            User.name.is_not(None),
        )
    )
    users = list(result.scalars().all())

    matched_user_ids: set[int] = set()
    for mention_token in mention_tokens:
        matched = [user for user in users if _matches_mention_token(user, mention_token)]
        if len(matched) == 1:
            matched_user_ids.add(int(matched[0].id))

    return matched_user_ids


async def _build_participant_user_ids(db: AsyncSession, comment: Comment) -> set[int]:
    if comment.daily_snippet_id is None and comment.weekly_snippet_id is None:
        return set()

    stmt = select(Comment.user_id).filter(Comment.id != comment.id)
    if comment.daily_snippet_id is not None:
        stmt = stmt.filter(Comment.daily_snippet_id == comment.daily_snippet_id)
    else:
        stmt = stmt.filter(Comment.weekly_snippet_id == comment.weekly_snippet_id)

    result = await db.execute(stmt)
    return {int(user_id) for user_id in result.scalars().all()}


async def _load_notification_settings(
    db: AsyncSession,
    recipient_user_ids: set[int],
) -> dict[int, NotificationSetting]:
    if not recipient_user_ids:
        return {}

    result = await db.execute(
        select(NotificationSetting).filter(NotificationSetting.user_id.in_(list(recipient_user_ids)))
    )
    settings = list(result.scalars().all())
    return {int(setting.user_id): setting for setting in settings}


def _is_enabled_for_reason(reason: str, setting: NotificationSetting | None) -> bool:
    if setting is None:
        return True
    if reason == "comment_on_my_snippet":
        return bool(setting.notify_post_author)
    if reason == "mention_in_comment":
        return bool(setting.notify_mentions)
    if reason == "comment_on_participated_snippet":
        return bool(setting.notify_participants)
    return False


def _resolve_notification_type(
    reasons: set[str],
    setting: NotificationSetting | None,
) -> str | None:
    ordered = (
        "mention_in_comment",
        "comment_on_my_snippet",
        "comment_on_participated_snippet",
    )
    for notification_type in ordered:
        if notification_type in reasons and _is_enabled_for_reason(notification_type, setting):
            return notification_type
    return None


def _build_dedupe_key(
    comment_id: int,
    recipient_user_id: int,
    notification_type: str,
) -> str:
    return (
        f"comment:{comment_id}:recipient:{recipient_user_id}:"
        f"type:{notification_type}"
    )


async def get_notification_setting(
    db: AsyncSession,
    user_id: int,
) -> Optional[NotificationSetting]:
    result = await db.execute(
        select(NotificationSetting).filter(NotificationSetting.user_id == user_id)
    )
    return result.scalars().first()


async def get_or_create_notification_setting(
    db: AsyncSession,
    user_id: int,
) -> NotificationSetting:
    existing = await get_notification_setting(db, user_id)
    if existing:
        return existing

    setting = NotificationSetting(user_id=user_id)
    db.add(setting)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await get_notification_setting(db, user_id)
        if existing:
            return existing
        raise

    refreshed = await get_notification_setting(db, user_id)
    return refreshed or setting


async def update_notification_setting(
    db: AsyncSession,
    setting: NotificationSetting,
    notify_post_author: Optional[bool] = None,
    notify_mentions: Optional[bool] = None,
    notify_participants: Optional[bool] = None,
) -> NotificationSetting:
    if notify_post_author is not None:
        setting.notify_post_author = notify_post_author
    if notify_mentions is not None:
        setting.notify_mentions = notify_mentions
    if notify_participants is not None:
        setting.notify_participants = notify_participants

    setting.updated_at = datetime.now(timezone.utc)
    await db.commit()

    refreshed = await get_notification_setting(db, setting.user_id)
    return refreshed or setting


async def create_comment_notifications(db: AsyncSession, comment: Comment) -> None:
    snippet_author_user_id = await _get_snippet_author_user_id(db, comment)

    actor_team_id = await _get_actor_team_id(db, comment.user_id)
    mention_tokens = _extract_mention_tokens(comment.content)
    mention_user_ids = await _build_mention_user_ids(db, mention_tokens, actor_team_id)
    participant_user_ids = await _build_participant_user_ids(db, comment)

    recipient_reasons: dict[int, set[str]] = defaultdict(set)
    if snippet_author_user_id is not None:
        recipient_reasons[snippet_author_user_id].add("comment_on_my_snippet")
    for user_id in mention_user_ids:
        recipient_reasons[user_id].add("mention_in_comment")
    for user_id in participant_user_ids:
        recipient_reasons[user_id].add("comment_on_participated_snippet")

    recipient_reasons.pop(comment.user_id, None)
    if not recipient_reasons:
        return

    settings_map = await _load_notification_settings(db, set(recipient_reasons.keys()))

    created_count = 0
    created_notifications: list[Notification] = []
    for recipient_user_id, reasons in recipient_reasons.items():
        setting = settings_map.get(recipient_user_id)
        notification_type = _resolve_notification_type(reasons, setting)
        if notification_type is None:
            continue

        savepoint = await db.begin_nested()
        try:
            notification = Notification(
                user_id=recipient_user_id,
                actor_user_id=comment.user_id,
                type=notification_type,
                daily_snippet_id=comment.daily_snippet_id,
                weekly_snippet_id=comment.weekly_snippet_id,
                comment_id=comment.id,
                dedupe_key=_build_dedupe_key(
                    comment_id=comment.id,
                    recipient_user_id=recipient_user_id,
                    notification_type=notification_type,
                ),
            )
            db.add(notification)
            await db.flush()
            await savepoint.commit()
            created_notifications.append(notification)
            created_count += 1
        except IntegrityError:
            await savepoint.rollback()

    if created_count > 0:
        await db.commit()

        for notification in created_notifications:
            await db.refresh(notification)
            await notification_registry.send_to_user(
                int(notification.user_id),
                {
                    "event": "notification",
                    "data": json.dumps(
                        {
                            "kind": "created",
                            "notification_id": int(notification.id),
                            "type": str(notification.type),
                            "comment_id": int(notification.comment_id) if notification.comment_id is not None else None,
                            "daily_snippet_id": int(notification.daily_snippet_id)
                            if notification.daily_snippet_id is not None
                            else None,
                            "weekly_snippet_id": int(notification.weekly_snippet_id)
                            if notification.weekly_snippet_id is not None
                            else None,
                            "created_at": notification.created_at.isoformat(),
                        },
                        ensure_ascii=False,
                    ),
                },
            )


async def list_notifications(
    db: AsyncSession,
    user_id: int,
    limit: int,
    offset: int,
) -> Tuple[list[Notification], int]:
    stmt = (
        select(Notification)
        .options(selectinload(Notification.actor_user))
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )

    total = await _count(db, stmt)
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = list(result.scalars().all())
    return items, total


async def get_notification_by_id_for_user(
    db: AsyncSession,
    notification_id: int,
    user_id: int,
) -> Optional[Notification]:
    result = await db.execute(
        select(Notification)
        .options(selectinload(Notification.actor_user))
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
    )
    return result.scalars().first()


async def mark_notification_as_read(
    db: AsyncSession,
    notification: Notification,
) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()

    refreshed = await get_notification_by_id_for_user(db, notification.id, notification.user_id)
    return refreshed or notification


async def mark_all_notifications_as_read(
    db: AsyncSession,
    user_id: int,
) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=now)
    )
    await db.commit()
    return int(result.rowcount or 0)


async def count_unread_notifications(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    return int(result.scalar_one())
