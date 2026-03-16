from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import crud
from app.models import AchievementGrant, Team, User
from app.achievement_rules import (
    ACHIEVEMENT_DEFINITIONS,
    ACHIEVEMENT_RULE_CODES,
    PERSONAL_STREAK_RULE_CODES,
    STREAK_RULE_CODES,
    TEAM_STREAK_RULE_CODES,
    WEEKLY_RULE_CODES,
    extract_grant_date_from_external_id,
    extract_team_id_from_external_id,
    is_daily_score_90,
    parse_total_score,
    resolve_personal_streak_user_ids,
    resolve_team_all_submitted_user_ids,
    resolve_team_streak_user_ids,
)
from app.achievement_time import resolve_default_target_date, target_week_from_date
from app.utils_time import BUSINESS_TIMEZONE, to_business_timezone


async def _count_existing_grants_for_prefix(db: AsyncSession, prefix: str) -> int:
    result = await db.execute(
        select(func.count(AchievementGrant.id)).filter(
            AchievementGrant.external_grant_id.is_not(None),
            AchievementGrant.external_grant_id.like(f"{prefix}%"),
        )
    )
    return int(result.scalar_one())


async def grant_daily_achievements(
    db: AsyncSession,
    *,
    target_date: date | None = None,
    now: datetime | None = None,
    dry_run: bool = False,
    process_weekly: bool | None = None,
) -> dict:
    now_kst = to_business_timezone(now or datetime.now(tz=BUSINESS_TIMEZONE))
    resolved_target_date = target_date or resolve_default_target_date(now_kst)
    is_monday = now_kst.weekday() == 0 if process_weekly is None else process_weekly
    target_week = target_week_from_date(resolved_target_date)
    daily_prefix = f"daily:{resolved_target_date.isoformat()}:"
    weekly_prefix = f"weekly:{target_week.isoformat()}:"

    streak_window_start_date = resolved_target_date - timedelta(days=99)

    if not dry_run:
        await crud.upsert_achievement_definitions(
            db,
            ACHIEVEMENT_DEFINITIONS,
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
    weekly_snippets = (
        await crud.list_weekly_snippets_for_week(db, target_week=target_week)
        if is_monday
        else []
    )

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
        grant_date = extract_grant_date_from_external_id(external_grant_id)
        if grant_date is None or grant_date == resolved_target_date:
            continue

        next_floor_date = grant_date + timedelta(days=1)
        if rule_code in rule_floor_date_by_user:
            existing_floor_date = rule_floor_date_by_user[rule_code].get(user_id)
            if existing_floor_date is None or next_floor_date > existing_floor_date:
                rule_floor_date_by_user[rule_code][user_id] = next_floor_date
            continue

        if rule_code in rule_floor_date_by_team:
            team_id = extract_team_id_from_external_id(external_grant_id)
            if team_id is None:
                continue
            existing_floor_date = rule_floor_date_by_team[rule_code].get(team_id)
            if existing_floor_date is None or next_floor_date > existing_floor_date:
                rule_floor_date_by_team[rule_code][team_id] = next_floor_date

    rank_candidate_user_ids = {
        int(snippet.user_id)
        for snippet in daily_snippets
    } | {
        int(snippet.user_id)
        for snippet in weekly_snippets
    }
    user_league_by_user_id: dict[int, str] = {}
    if rank_candidate_user_ids:
        user_league_rows = (
            await db.execute(
                select(User.id, User.team_id, User.league_type, Team.league_type)
                .outerjoin(Team, Team.id == User.team_id)
                .filter(User.id.in_(rank_candidate_user_ids))
            )
        ).all()
        for row in user_league_rows:
            if row.team_id is not None:
                league_type = row[3] or "none"
            else:
                league_type = row[2] or "none"
            user_league_by_user_id[int(row.id)] = str(league_type)

    daily_max_score_by_league: dict[str, float] = {}
    for snippet in daily_snippets:
        league_type = user_league_by_user_id.get(int(snippet.user_id), "none")
        if league_type == "none":
            continue
        score = parse_total_score(getattr(snippet, "feedback", None))
        if score > daily_max_score_by_league.get(league_type, 0.0):
            daily_max_score_by_league[league_type] = score

    weekly_max_score_by_league: dict[str, float] = {}
    for snippet in weekly_snippets:
        league_type = user_league_by_user_id.get(int(snippet.user_id), "none")
        if league_type == "none":
            continue
        score = parse_total_score(getattr(snippet, "feedback", None))
        if score > weekly_max_score_by_league.get(league_type, 0.0):
            weekly_max_score_by_league[league_type] = score

    daily_rank_1_user_ids = {
        int(snippet.user_id)
        for snippet in daily_snippets
        if (
            (league_type := user_league_by_user_id.get(int(snippet.user_id), "none")) != "none"
            and daily_max_score_by_league.get(league_type, 0.0) > 0.0
            and parse_total_score(getattr(snippet, "feedback", None))
            == daily_max_score_by_league.get(league_type, 0.0)
        )
    }
    weekly_rank_1_user_ids = {
        int(snippet.user_id)
        for snippet in weekly_snippets
        if (
            (league_type := user_league_by_user_id.get(int(snippet.user_id), "none")) != "none"
            and weekly_max_score_by_league.get(league_type, 0.0) > 0.0
            and parse_total_score(getattr(snippet, "feedback", None))
            == weekly_max_score_by_league.get(league_type, 0.0)
        )
    }

    daily_submitted_user_ids = {snippet.user_id for snippet in daily_snippets}
    weekly_submitted_user_ids = {snippet.user_id for snippet in weekly_snippets}

    personal_streak_rule_user_ids = resolve_personal_streak_user_ids(
        date_set_by_user_id=date_set_by_user_id,
        target_date=resolved_target_date,
        rule_floor_date_by_user=rule_floor_date_by_user,
    )
    team_streak_rule_team_user_ids = resolve_team_streak_user_ids(
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
                if is_daily_score_90(snippet)
            }
        ),
        "weekly_submitted": sorted(weekly_submitted_user_ids),
        "daily_rank_1": sorted(daily_rank_1_user_ids),
        "weekly_rank_1": sorted(weekly_rank_1_user_ids),
        "daily_team_all_submitted": resolve_team_all_submitted_user_ids(
            daily_submitted_user_ids,
            team_member_ids_by_team,
        ),
        "weekly_team_all_submitted": resolve_team_all_submitted_user_ids(
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

        grant_prefix = weekly_prefix if code in WEEKLY_RULE_CODES else daily_prefix

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
                            "external_grant_id": f"{grant_prefix}{code}:team:{team_id}:user:{user_id}",
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
                    "external_grant_id": f"{grant_prefix}{code}:user:{user_id}",
                }
            )

    skipped_missing_definition_grants_count = sum(
        len(rule_user_ids.get(code, [])) for code in missing_definition_codes
    )

    if dry_run:
        daily_deleted_count = await _count_existing_grants_for_prefix(db, daily_prefix)
        weekly_deleted_count = (
            await _count_existing_grants_for_prefix(db, weekly_prefix)
            if is_monday
            else 0
        )
        deleted_count = daily_deleted_count + weekly_deleted_count
        created_count = len(grants_to_create)
    else:
        daily_deleted_count = await crud.delete_achievement_grants_for_external_prefix(
            db,
            daily_prefix,
            commit=False,
        )
        weekly_deleted_count = (
            await crud.delete_achievement_grants_for_external_prefix(
                db,
                weekly_prefix,
                commit=False,
            )
            if is_monday
            else 0
        )
        deleted_count = daily_deleted_count + weekly_deleted_count
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
        "weekly_processed": is_monday,
        "daily_prefix": daily_prefix,
        "weekly_prefix": weekly_prefix,
        "deleted_count": deleted_count,
        "created_count": created_count,
        "rule_candidate_counts": rule_candidate_counts,
        "rule_created_counts": rule_created_counts,
        "missing_definition_codes": missing_definition_codes,
        "skipped_missing_definition_codes_count": len(missing_definition_codes),
        "skipped_missing_definition_grants_count": skipped_missing_definition_grants_count,
    }
