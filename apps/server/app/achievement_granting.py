from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import crud
from app.models import AchievementGrant, User
from app.utils_time import (
    BUSINESS_TIMEZONE,
    current_business_date,
    current_business_week_start,
    to_business_timezone,
)


ACHIEVEMENT_RULE_CODES = (
    "daily_submitted",
    "daily_score_90",
    "weekly_submitted",
    "daily_rank_1",
    "weekly_rank_1",
    "daily_team_all_submitted",
    "weekly_team_all_submitted",
    "daily_streak_7",
    "daily_streak_28",
    "daily_streak_100",
    "team_daily_streak_7",
    "team_daily_streak_28",
)

PERSONAL_STREAK_RULE_THRESHOLDS: tuple[tuple[str, int], ...] = (
    ("daily_streak_7", 7),
    ("daily_streak_28", 28),
    ("daily_streak_100", 100),
)

TEAM_STREAK_RULE_THRESHOLDS: tuple[tuple[str, int], ...] = (
    ("team_daily_streak_7", 7),
    ("team_daily_streak_28", 28),
)

TEAM_STREAK_RULE_CODES = tuple(code for code, _ in TEAM_STREAK_RULE_THRESHOLDS)
PERSONAL_STREAK_RULE_CODES = tuple(code for code, _ in PERSONAL_STREAK_RULE_THRESHOLDS)
STREAK_RULE_CODES = PERSONAL_STREAK_RULE_CODES + TEAM_STREAK_RULE_CODES

STREAK_ACHIEVEMENT_DEFINITIONS: tuple[dict, ...] = (
    {
        "code": "daily_streak_7",
        "name": "Daily Streak 7",
        "description": "7일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://example.com/achievements/daily-streak-7.png",
        "rarity": "rare",
        "is_public_announceable": True,
    },
    {
        "code": "daily_streak_28",
        "name": "Daily Streak 28",
        "description": "28일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://example.com/achievements/daily-streak-28.png",
        "rarity": "epic",
        "is_public_announceable": True,
    },
    {
        "code": "daily_streak_100",
        "name": "Daily Streak 100",
        "description": "100일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://example.com/achievements/daily-streak-100.png",
        "rarity": "legend",
        "is_public_announceable": True,
    },
    {
        "code": "team_daily_streak_7",
        "name": "Team Daily Streak 7",
        "description": "팀원 전원이 7일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://example.com/achievements/team-daily-streak-7.png",
        "rarity": "epic",
        "is_public_announceable": True,
    },
    {
        "code": "team_daily_streak_28",
        "name": "Team Daily Streak 28",
        "description": "팀원 전원이 28일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://example.com/achievements/team-daily-streak-28.png",
        "rarity": "legend",
        "is_public_announceable": True,
    },
)


def resolve_default_target_date(now: datetime | None = None) -> date:
    now_kst = to_business_timezone(now or datetime.now(tz=BUSINESS_TIMEZONE))
    return current_business_date(now_kst) - timedelta(days=1)


def _target_week_from_date(target_date: date) -> date:
    reference_now = datetime.combine(target_date, time(hour=12), tzinfo=BUSINESS_TIMEZONE)
    return current_business_week_start(reference_now)


def _parse_total_score(feedback: str | None) -> float:
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


def _is_daily_score_90(snippet) -> bool:
    return _parse_total_score(getattr(snippet, "feedback", None)) >= 90.0


async def _count_existing_grants_for_prefix(db: AsyncSession, prefix: str) -> int:
    result = await db.execute(
        select(func.count(AchievementGrant.id)).filter(
            AchievementGrant.external_grant_id.is_not(None),
            AchievementGrant.external_grant_id.like(f"{prefix}%"),
        )
    )
    return int(result.scalar_one())


def _resolve_team_all_submitted_user_ids(
    user_ids_with_snippet: set[int],
    team_member_ids_by_team: dict[int, set[int]],
) -> list[int]:
    qualified_user_ids: set[int] = set()
    for member_ids in team_member_ids_by_team.values():
        if len(member_ids) < 2:
            continue
        if member_ids.issubset(user_ids_with_snippet):
            qualified_user_ids.update(member_ids)
    return sorted(qualified_user_ids)


def _extract_grant_date_from_external_id(external_grant_id: str) -> date | None:
    parts = external_grant_id.split(":")
    if len(parts) < 3 or parts[0] != "daily":
        return None

    try:
        return date.fromisoformat(parts[1])
    except ValueError:
        return None


def _extract_team_id_from_external_id(external_grant_id: str) -> int | None:
    parts = external_grant_id.split(":")
    for index, token in enumerate(parts[:-1]):
        if token != "team":
            continue
        try:
            return int(parts[index + 1])
        except (TypeError, ValueError):
            return None
    return None


def _count_consecutive_dates(
    submitted_dates: set[date],
    target_date: date,
    floor_date: date,
) -> int:
    if target_date < floor_date:
        return 0

    count = 0
    current = target_date
    while current >= floor_date and current in submitted_dates:
        count += 1
        current -= timedelta(days=1)
    return count


def _resolve_personal_streak_user_ids(
    date_set_by_user_id: dict[int, set[date]],
    target_date: date,
    rule_floor_date_by_user: dict[str, dict[int, date]],
) -> dict[str, list[int]]:
    resolved: dict[str, list[int]] = {code: [] for code in PERSONAL_STREAK_RULE_CODES}

    for user_id, submitted_dates in date_set_by_user_id.items():
        if target_date not in submitted_dates:
            continue

        for rule_code, threshold in PERSONAL_STREAK_RULE_THRESHOLDS:
            floor_date = rule_floor_date_by_user[rule_code].get(user_id, date.min)
            consecutive_days = _count_consecutive_dates(
                submitted_dates=submitted_dates,
                target_date=target_date,
                floor_date=floor_date,
            )
            if consecutive_days >= threshold:
                resolved[rule_code].append(user_id)

    for code in resolved:
        resolved[code] = sorted(resolved[code])
    return resolved


def _resolve_team_streak_user_ids(
    date_set_by_user_id: dict[int, set[date]],
    team_member_ids_by_team: dict[int, set[int]],
    target_date: date,
    rule_floor_date_by_team: dict[str, dict[int, date]],
) -> dict[str, dict[int, list[int]]]:
    resolved: dict[str, dict[int, list[int]]] = {
        code: {}
        for code in TEAM_STREAK_RULE_CODES
    }

    for team_id, member_ids in team_member_ids_by_team.items():
        if len(member_ids) < 2:
            continue

        member_submitted_date_sets = [date_set_by_user_id.get(member_id, set()) for member_id in member_ids]
        if not member_submitted_date_sets:
            continue

        team_success_dates = set.intersection(*member_submitted_date_sets)
        if target_date not in team_success_dates:
            continue

        for rule_code, threshold in TEAM_STREAK_RULE_THRESHOLDS:
            floor_date = rule_floor_date_by_team[rule_code].get(team_id, date.min)
            consecutive_days = _count_consecutive_dates(
                submitted_dates=team_success_dates,
                target_date=target_date,
                floor_date=floor_date,
            )
            if consecutive_days >= threshold:
                resolved[rule_code][team_id] = sorted(member_ids)

    return resolved


async def grant_daily_achievements(
    db: AsyncSession,
    *,
    target_date: date | None = None,
    now: datetime | None = None,
    dry_run: bool = False,
) -> dict:
    now_kst = to_business_timezone(now or datetime.now(tz=BUSINESS_TIMEZONE))
    resolved_target_date = target_date or resolve_default_target_date(now_kst)
    target_week = _target_week_from_date(resolved_target_date)
    prefix = f"daily:{resolved_target_date.isoformat()}:"

    streak_window_start_date = resolved_target_date - timedelta(days=99)

    if not dry_run:
        await crud.upsert_achievement_definitions(
            db,
            STREAK_ACHIEVEMENT_DEFINITIONS,
            commit=False,
        )

    definitions_by_code = await crud.get_achievement_definitions_by_codes(db, list(ACHIEVEMENT_RULE_CODES))
    missing_definition_codes = [
        code for code in ACHIEVEMENT_RULE_CODES if code not in definitions_by_code
    ]

    daily_snippets = await crud.list_daily_snippets_for_date(db, target_date=resolved_target_date)
    daily_snippets_in_range = await crud.list_daily_snippets_in_range(
        db,
        start_date=streak_window_start_date,
        end_date=resolved_target_date,
    )
    weekly_snippets = await crud.list_weekly_snippets_for_week(db, target_week=target_week)

    team_rows = (
        await db.execute(
            select(User.id, User.team_id)
            .filter(User.team_id.is_not(None))
            .order_by(User.team_id.asc(), User.id.asc())
        )
    ).all()
    team_member_ids_by_team: dict[int, set[int]] = {}
    for row in team_rows:
        if row.team_id is None:
            continue
        team_member_ids_by_team.setdefault(int(row.team_id), set()).add(int(row.id))

    date_set_by_user_id: dict[int, set[date]] = {}
    for snippet in daily_snippets_in_range:
        date_set_by_user_id.setdefault(int(snippet.user_id), set()).add(snippet.date)

    rule_floor_date_by_user: dict[str, dict[int, date]] = {
        code: {}
        for code in PERSONAL_STREAK_RULE_CODES
    }
    rule_floor_date_by_team: dict[str, dict[int, date]] = {
        code: {}
        for code in TEAM_STREAK_RULE_CODES
    }
    streak_grant_histories = await crud.list_achievement_grant_histories_for_rule_codes(
        db,
        STREAK_RULE_CODES,
    )
    for rule_code, user_id, external_grant_id in streak_grant_histories:
        grant_date = _extract_grant_date_from_external_id(external_grant_id)
        if grant_date is None or grant_date == resolved_target_date:
            continue

        next_floor_date = grant_date + timedelta(days=1)
        if rule_code in rule_floor_date_by_user:
            existing_floor_date = rule_floor_date_by_user[rule_code].get(user_id)
            if existing_floor_date is None or next_floor_date > existing_floor_date:
                rule_floor_date_by_user[rule_code][user_id] = next_floor_date
            continue

        if rule_code in rule_floor_date_by_team:
            team_id = _extract_team_id_from_external_id(external_grant_id)
            if team_id is None:
                continue
            existing_floor_date = rule_floor_date_by_team[rule_code].get(team_id)
            if existing_floor_date is None or next_floor_date > existing_floor_date:
                rule_floor_date_by_team[rule_code][team_id] = next_floor_date

    daily_rank_1_score = max(
        (_parse_total_score(getattr(snippet, "feedback", None)) for snippet in daily_snippets),
        default=0.0,
    )
    weekly_rank_1_score = max(
        (_parse_total_score(getattr(snippet, "feedback", None)) for snippet in weekly_snippets),
        default=0.0,
    )

    daily_submitted_user_ids = {snippet.user_id for snippet in daily_snippets}
    weekly_submitted_user_ids = {snippet.user_id for snippet in weekly_snippets}

    personal_streak_rule_user_ids = _resolve_personal_streak_user_ids(
        date_set_by_user_id=date_set_by_user_id,
        target_date=resolved_target_date,
        rule_floor_date_by_user=rule_floor_date_by_user,
    )
    team_streak_rule_team_user_ids = _resolve_team_streak_user_ids(
        date_set_by_user_id=date_set_by_user_id,
        team_member_ids_by_team=team_member_ids_by_team,
        target_date=resolved_target_date,
        rule_floor_date_by_team=rule_floor_date_by_team,
    )

    rule_user_ids: dict[str, list[int]] = {
        "daily_submitted": sorted(daily_submitted_user_ids),
        "daily_score_90": sorted(
            {
                snippet.user_id
                for snippet in daily_snippets
                if _is_daily_score_90(snippet)
            }
        ),
        "weekly_submitted": sorted(weekly_submitted_user_ids),
        "daily_rank_1": sorted(
            {
                snippet.user_id
                for snippet in daily_snippets
                if _parse_total_score(getattr(snippet, "feedback", None)) == daily_rank_1_score
            }
        )
        if daily_rank_1_score > 0.0
        else [],
        "weekly_rank_1": sorted(
            {
                snippet.user_id
                for snippet in weekly_snippets
                if _parse_total_score(getattr(snippet, "feedback", None)) == weekly_rank_1_score
            }
        )
        if weekly_rank_1_score > 0.0
        else [],
        "daily_team_all_submitted": _resolve_team_all_submitted_user_ids(
            daily_submitted_user_ids,
            team_member_ids_by_team,
        ),
        "weekly_team_all_submitted": _resolve_team_all_submitted_user_ids(
            weekly_submitted_user_ids,
            team_member_ids_by_team,
        ),
        **personal_streak_rule_user_ids,
    }

    for code in TEAM_STREAK_RULE_CODES:
        team_user_ids = team_streak_rule_team_user_ids.get(code, {})
        rule_user_ids[code] = sorted(
            {
                user_id
                for member_ids in team_user_ids.values()
                for user_id in member_ids
            }
        )

    rule_candidate_counts = {
        code: len(rule_user_ids.get(code, [])) for code in ACHIEVEMENT_RULE_CODES
    }

    grants_to_create: list[dict] = []
    rule_created_counts = {code: 0 for code in ACHIEVEMENT_RULE_CODES}

    for code in ACHIEVEMENT_RULE_CODES:
        definition = definitions_by_code.get(code)
        if definition is None:
            continue

        if code in TEAM_STREAK_RULE_CODES:
            created_count_for_code = 0
            for team_id, member_ids in sorted(team_streak_rule_team_user_ids.get(code, {}).items()):
                for user_id in member_ids:
                    grants_to_create.append(
                        {
                            "user_id": user_id,
                            "achievement_definition_id": definition.id,
                            "granted_at": now_kst,
                            "publish_start_at": now_kst,
                            "publish_end_at": None,
                            "external_grant_id": f"{prefix}{code}:team:{team_id}:user:{user_id}",
                        }
                    )
                    created_count_for_code += 1
            rule_created_counts[code] = created_count_for_code
            continue

        user_ids = rule_user_ids.get(code, [])
        rule_created_counts[code] = len(user_ids)

        for user_id in user_ids:
            grants_to_create.append(
                {
                    "user_id": user_id,
                    "achievement_definition_id": definition.id,
                    "granted_at": now_kst,
                    "publish_start_at": now_kst,
                    "publish_end_at": None,
                    "external_grant_id": f"{prefix}{code}:user:{user_id}",
                }
            )

    skipped_missing_definition_grants_count = sum(
        len(rule_user_ids.get(code, [])) for code in missing_definition_codes
    )

    if dry_run:
        deleted_count = await _count_existing_grants_for_prefix(db, prefix)
        created_count = len(grants_to_create)
    else:
        deleted_count = await crud.delete_achievement_grants_for_external_prefix(
            db,
            prefix,
            commit=False,
        )
        created_rows = await crud.bulk_create_achievement_grants(
            db,
            grants_to_create,
            commit=False,
        )
        await db.commit()
        created_count = len(created_rows)

    return {
        "target_date": resolved_target_date,
        "target_week": target_week,
        "dry_run": dry_run,
        "external_prefix": prefix,
        "deleted_count": deleted_count,
        "created_count": created_count,
        "rule_candidate_counts": rule_candidate_counts,
        "rule_created_counts": rule_created_counts,
        "missing_definition_codes": missing_definition_codes,
        "skipped_missing_definition_codes_count": len(missing_definition_codes),
        "skipped_missing_definition_grants_count": skipped_missing_definition_grants_count,
    }
