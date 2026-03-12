from __future__ import annotations

import json
from datetime import date, timedelta

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

BASE_ACHIEVEMENT_DEFINITIONS: tuple[dict, ...] = (
    {
        "code": "daily_submitted",
        "name": "데일리 제출",
        "description": "데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/daily_submitted.png",
        "rarity": "common",
        "is_public_announceable": False,
    },
    {
        "code": "daily_score_90",
        "name": "데일리 점수 90",
        "description": "데일리 피드백 점수 90점 이상을 달성했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/daily_score_90.png",
        "rarity": "rare",
        "is_public_announceable": True,
    },
    {
        "code": "weekly_submitted",
        "name": "위클리 제출",
        "description": "위클리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/weekly_submitted.png",
        "rarity": "uncommon",
        "is_public_announceable": False,
    },
    {
        "code": "daily_rank_1",
        "name": "데일리 1위",
        "description": "데일리 리더보드 1위를 달성했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/daily_rank_1.png",
        "rarity": "uncommon",
        "is_public_announceable": True,
    },
    {
        "code": "weekly_rank_1",
        "name": "위클리 1위",
        "description": "위클리 리더보드 1위를 달성했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/weekly_rank_1.png",
        "rarity": "epic",
        "is_public_announceable": True,
    },
    {
        "code": "daily_team_all_submitted",
        "name": "데일리 팀 전원 제출",
        "description": "같은 팀원 전원이 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/daily_team_all_submitted.png",
        "rarity": "uncommon",
        "is_public_announceable": True,
    },
    {
        "code": "weekly_team_all_submitted",
        "name": "위클리 팀 전원 제출",
        "description": "같은 팀원 전원이 위클리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/weekly_team_all_submitted.png",
        "rarity": "rare",
        "is_public_announceable": True,
    },
)

STREAK_ACHIEVEMENT_DEFINITIONS: tuple[dict, ...] = (
    {
        "code": "daily_streak_7",
        "name": "데일리 7일 연속",
        "description": "7일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/daily_streak_7.png",
        "rarity": "rare",
        "is_public_announceable": True,
    },
    {
        "code": "daily_streak_28",
        "name": "데일리 28일 연속",
        "description": "28일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/daily_streak_28.png",
        "rarity": "epic",
        "is_public_announceable": True,
    },
    {
        "code": "daily_streak_100",
        "name": "데일리 100일 연속",
        "description": "100일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/daily_streak_100.png",
        "rarity": "legend",
        "is_public_announceable": True,
    },
    {
        "code": "team_daily_streak_7",
        "name": "팀 데일리 7일 연속",
        "description": "팀원 전원이 7일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/team_daily_streak_7.png",
        "rarity": "epic",
        "is_public_announceable": True,
    },
    {
        "code": "team_daily_streak_28",
        "name": "팀 데일리 28일 연속",
        "description": "팀원 전원이 28일 연속으로 데일리 스니펫을 제출했습니다.",
        "badge_image_url": "https://assets.1000.school/achievements/v1/team_daily_streak_28.png",
        "rarity": "legend",
        "is_public_announceable": True,
    },
)

ACHIEVEMENT_DEFINITIONS: tuple[dict, ...] = (
    *BASE_ACHIEVEMENT_DEFINITIONS,
    *STREAK_ACHIEVEMENT_DEFINITIONS,
)


def parse_total_score(feedback: str | None) -> float:
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


def is_daily_score_90(snippet) -> bool:
    return parse_total_score(getattr(snippet, "feedback", None)) >= 90.0


def resolve_team_all_submitted_user_ids(
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


def extract_grant_date_from_external_id(external_grant_id: str) -> date | None:
    parts = external_grant_id.split(":")
    if len(parts) < 3 or parts[0] != "daily":
        return None

    try:
        return date.fromisoformat(parts[1])
    except ValueError:
        return None


def extract_team_id_from_external_id(external_grant_id: str) -> int | None:
    parts = external_grant_id.split(":")
    for index, token in enumerate(parts[:-1]):
        if token != "team":
            continue
        try:
            return int(parts[index + 1])
        except (TypeError, ValueError):
            return None
    return None


def count_consecutive_dates(
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


def resolve_personal_streak_user_ids(
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
            consecutive_days = count_consecutive_dates(
                submitted_dates=submitted_dates,
                target_date=target_date,
                floor_date=floor_date,
            )
            if consecutive_days >= threshold:
                resolved[rule_code].append(user_id)

    for code in resolved:
        resolved[code] = sorted(resolved[code])
    return resolved


def resolve_team_streak_user_ids(
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
            consecutive_days = count_consecutive_dates(
                submitted_dates=team_success_dates,
                target_date=target_date,
                floor_date=floor_date,
            )
            if consecutive_days >= threshold:
                resolved[rule_code][team_id] = sorted(member_ids)

    return resolved
