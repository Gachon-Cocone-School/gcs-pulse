from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.achievement_granting import grant_daily_achievements
from app.models import Base, AchievementDefinition, AchievementGrant, DailySnippet, Team, User, WeeklySnippet


async def _create_test_session_factory(tmp_path, name: str = "achievement_granting"):
    db_path = tmp_path / f"{name}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_achievement_grants_external_grant_id "
                "ON achievement_grants(external_grant_id) "
                "WHERE external_grant_id IS NOT NULL"
            )
        )

    return engine, async_sessionmaker(bind=engine, expire_on_commit=False)


async def _seed_users_and_definitions(db):
    team_a = Team(name="Team A", invite_code="TEAMA001")
    team_b = Team(name="Team B", invite_code="TEAMB001")
    db.add_all([team_a, team_b])
    await db.flush()

    users = [
        User(google_sub="u1", email="u1@example.com", name="U1", team_id=team_a.id),
        User(google_sub="u2", email="u2@example.com", name="U2", team_id=team_a.id),
        User(google_sub="u3", email="u3@example.com", name="U3", team_id=team_b.id),
    ]
    db.add_all(users)
    await db.flush()

    defs = [
        AchievementDefinition(
            code="daily_submitted",
            name="Daily Submitted",
            description="Daily snippet submitted",
            badge_image_url="https://example.com/daily-submitted.png",
            rarity="common",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="daily_score_90",
            name="Daily Score 90",
            description="Daily score 90+",
            badge_image_url="https://example.com/daily-score-90.png",
            rarity="rare",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="weekly_submitted",
            name="Weekly Submitted",
            description="Weekly snippet submitted",
            badge_image_url="https://example.com/weekly-submitted.png",
            rarity="uncommon",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="daily_rank_1",
            name="Daily Rank 1",
            description="Daily top score",
            badge_image_url="https://example.com/daily-rank-1.png",
            rarity="uncommon",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="weekly_rank_1",
            name="Weekly Rank 1",
            description="Weekly top score",
            badge_image_url="https://example.com/weekly-rank-1.png",
            rarity="epic",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="daily_team_all_submitted",
            name="Daily Team All Submitted",
            description="All team members submitted daily snippets",
            badge_image_url="https://example.com/daily-team-all-submitted.png",
            rarity="uncommon",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="weekly_team_all_submitted",
            name="Weekly Team All Submitted",
            description="All team members submitted weekly snippets",
            badge_image_url="https://example.com/weekly-team-all-submitted.png",
            rarity="uncommon",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="daily_streak_7",
            name="Daily Streak 7",
            description="7-day personal streak",
            badge_image_url="https://example.com/daily-streak-7.png",
            rarity="rare",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="daily_streak_28",
            name="Daily Streak 28",
            description="28-day personal streak",
            badge_image_url="https://example.com/daily-streak-28.png",
            rarity="epic",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="daily_streak_100",
            name="Daily Streak 100",
            description="100-day personal streak",
            badge_image_url="https://example.com/daily-streak-100.png",
            rarity="legend",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="team_daily_streak_7",
            name="Team Daily Streak 7",
            description="7-day team streak",
            badge_image_url="https://example.com/team-daily-streak-7.png",
            rarity="epic",
            is_public_announceable=True,
        ),
        AchievementDefinition(
            code="team_daily_streak_28",
            name="Team Daily Streak 28",
            description="28-day team streak",
            badge_image_url="https://example.com/team-daily-streak-28.png",
            rarity="legend",
            is_public_announceable=True,
        ),
    ]
    db.add_all(defs)
    await db.flush()

    return users


async def _seed_daily_weekly(db, users, target_date: date, target_week: date):
    db.add_all(
        [
            DailySnippet(
                user_id=users[0].id,
                date=target_date,
                content="u1 daily",
                feedback='{"total_score": 89.9}',
            ),
            DailySnippet(
                user_id=users[1].id,
                date=target_date,
                content="u2 daily",
                feedback='{"total_score": 90.0}',
            ),
            WeeklySnippet(
                user_id=users[0].id,
                week=target_week,
                content="u1 weekly",
                feedback='{"total_score": 70}',
            ),
            WeeklySnippet(
                user_id=users[2].id,
                week=target_week,
                content="u3 weekly",
                feedback='{"total_score": 80}',
            ),
        ]
    )
    await db.commit()


async def _count_grants(db):
    rows = (await db.execute(text("SELECT COUNT(*) FROM achievement_grants"))).scalar_one()
    return int(rows)


async def _count_grants_with_prefix(db, prefix: str):
    rows = (
        await db.execute(
            text(
                "SELECT COUNT(*) FROM achievement_grants "
                "WHERE external_grant_id LIKE :prefix"
            ),
            {"prefix": f"{prefix}%"},
        )
    ).scalar_one()
    return int(rows)


async def _get_external_ids(db):
    rows = (
        await db.execute(
            text("SELECT external_grant_id FROM achievement_grants ORDER BY external_grant_id ASC")
        )
    ).scalars().all()
    return [row for row in rows if row is not None]


async def _seed_daily_streak(
    db,
    user_id: int,
    end_date: date,
    days: int,
    content_prefix: str = "daily",
):
    db.add_all(
        [
            DailySnippet(
                user_id=user_id,
                date=end_date - timedelta(days=offset),
                content=f"{content_prefix}-{offset}",
                feedback='{"total_score": 80}',
            )
            for offset in range(days)
        ]
    )


def test_first_run_creates_rule_based_grants(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_test_session_factory(tmp_path, "first_run")
        try:
            target_date = date(2026, 2, 23)
            target_week = date(2026, 2, 23) - timedelta(days=date(2026, 2, 23).weekday())
            now = datetime(2026, 2, 24, 10, 0, tzinfo=timezone(timedelta(hours=9)))

            async with SessionLocal() as db:
                users = await _seed_users_and_definitions(db)
                await _seed_daily_weekly(db, users, target_date, target_week)

                summary = await grant_daily_achievements(
                    db,
                    target_date=target_date,
                    now=now,
                    dry_run=False,
                )

                assert summary["created_count"] == 9
                assert summary["deleted_count"] == 0
                assert summary["missing_definition_codes"] == []
                assert summary["rule_candidate_counts"] == {
                    "daily_submitted": 2,
                    "daily_score_90": 1,
                    "weekly_submitted": 2,
                    "daily_rank_1": 1,
                    "weekly_rank_1": 1,
                    "daily_team_all_submitted": 2,
                    "weekly_team_all_submitted": 0,
                    "daily_streak_7": 0,
                    "daily_streak_28": 0,
                    "daily_streak_100": 0,
                    "team_daily_streak_7": 0,
                    "team_daily_streak_28": 0,
                }
                assert summary["rule_created_counts"] == {
                    "daily_submitted": 2,
                    "daily_score_90": 1,
                    "weekly_submitted": 2,
                    "daily_rank_1": 1,
                    "weekly_rank_1": 1,
                    "daily_team_all_submitted": 2,
                    "weekly_team_all_submitted": 0,
                    "daily_streak_7": 0,
                    "daily_streak_28": 0,
                    "daily_streak_100": 0,
                    "team_daily_streak_7": 0,
                    "team_daily_streak_28": 0,
                }

                total = await _count_grants(db)
                assert total == 9

                prefix = f"daily:{target_date.isoformat()}:"
                per_prefix = await _count_grants_with_prefix(db, prefix)
                assert per_prefix == 9

                external_ids = await _get_external_ids(db)
                assert f"{prefix}daily_submitted:user:{users[0].id}" in external_ids
                assert f"{prefix}daily_submitted:user:{users[1].id}" in external_ids
                assert f"{prefix}daily_score_90:user:{users[1].id}" in external_ids
                assert f"{prefix}weekly_submitted:user:{users[0].id}" in external_ids
                assert f"{prefix}weekly_submitted:user:{users[2].id}" in external_ids
                assert f"{prefix}daily_rank_1:user:{users[1].id}" in external_ids
                assert f"{prefix}weekly_rank_1:user:{users[2].id}" in external_ids
                assert f"{prefix}daily_team_all_submitted:user:{users[0].id}" in external_ids
                assert f"{prefix}daily_team_all_submitted:user:{users[1].id}" in external_ids
                assert f"{prefix}weekly_team_all_submitted:user:{users[2].id}" not in external_ids
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_same_target_date_rewrites_existing_grants(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_test_session_factory(tmp_path, "rewrite_run")
        try:
            target_date = date(2026, 2, 23)
            target_week = date(2026, 2, 23) - timedelta(days=date(2026, 2, 23).weekday())
            now = datetime(2026, 2, 24, 10, 0, tzinfo=timezone(timedelta(hours=9)))

            async with SessionLocal() as db:
                users = await _seed_users_and_definitions(db)
                await _seed_daily_weekly(db, users, target_date, target_week)

                defs = (
                    await db.execute(
                        text("SELECT id, code FROM achievement_definitions")
                    )
                ).all()
                code_to_id = {row.code: row.id for row in defs}
                db.add(
                    AchievementGrant(
                        user_id=users[0].id,
                        achievement_definition_id=code_to_id["daily_submitted"],
                        granted_at=now,
                        publish_start_at=now,
                        publish_end_at=None,
                        external_grant_id="manual:outside-prefix",
                    )
                )
                await db.commit()

                first = await grant_daily_achievements(db, target_date=target_date, now=now, dry_run=False)
                assert first["created_count"] == 9

                before_ids = await _get_external_ids(db)
                prefix = f"daily:{target_date.isoformat()}:"
                assert len([v for v in before_ids if v.startswith(prefix)]) == 9

                second = await grant_daily_achievements(db, target_date=target_date, now=now, dry_run=False)
                assert second["deleted_count"] == 9
                assert second["created_count"] == 9

                after_ids = await _get_external_ids(db)
                assert "manual:outside-prefix" in after_ids
                assert len([v for v in after_ids if v.startswith(prefix)]) == 9
                assert len(after_ids) == 10
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_daily_score_90_boundary(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_test_session_factory(tmp_path, "score_boundary")
        try:
            target_date = date(2026, 2, 23)
            now = datetime(2026, 2, 24, 10, 0, tzinfo=timezone(timedelta(hours=9)))

            async with SessionLocal() as db:
                users = [
                    User(google_sub="s1", email="s1@example.com", name="S1"),
                    User(google_sub="s2", email="s2@example.com", name="S2"),
                ]
                db.add_all(users)
                await db.flush()

                db.add(
                    AchievementDefinition(
                        code="daily_score_90",
                        name="Daily Score 90",
                        description="Daily score 90+",
                        badge_image_url="https://example.com/daily-score-90.png",
                        rarity="rare",
                        is_public_announceable=True,
                    )
                )
                await db.flush()

                db.add_all(
                    [
                        DailySnippet(
                            user_id=users[0].id,
                            date=target_date,
                            content="s1",
                            feedback='{"total_score": 89.9}',
                        ),
                        DailySnippet(
                            user_id=users[1].id,
                            date=target_date,
                            content="s2",
                            feedback='{"total_score": 90.0}',
                        ),
                    ]
                )
                await db.commit()

                summary = await grant_daily_achievements(
                    db,
                    target_date=target_date,
                    now=now,
                    dry_run=False,
                )

                assert summary["rule_candidate_counts"]["daily_score_90"] == 1
                assert summary["rule_created_counts"]["daily_score_90"] == 1

                prefix = f"daily:{target_date.isoformat()}:daily_score_90:user:"
                ids = await _get_external_ids(db)
                matched = [item for item in ids if item.startswith(prefix)]
                assert len(matched) == 1
                assert matched[0].endswith(str(users[1].id))
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_missing_definition_codes_are_skipped(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_test_session_factory(tmp_path, "missing_defs")
        try:
            target_date = date(2026, 2, 23)
            target_week = date(2026, 2, 23) - timedelta(days=date(2026, 2, 23).weekday())
            now = datetime(2026, 2, 24, 10, 0, tzinfo=timezone(timedelta(hours=9)))

            async with SessionLocal() as db:
                team = Team(name="Missing Team", invite_code="MISS0001")
                db.add(team)
                await db.flush()

                user = User(google_sub="m1", email="m1@example.com", name="M1", team_id=team.id)
                db.add(user)
                await db.flush()

                db.add(
                    AchievementDefinition(
                        code="daily_submitted",
                        name="Daily Submitted",
                        description="Daily snippet submitted",
                        badge_image_url="https://example.com/daily-submitted.png",
                        rarity="common",
                        is_public_announceable=True,
                    )
                )
                await db.flush()

                db.add(
                    DailySnippet(
                        user_id=user.id,
                        date=target_date,
                        content="m1 daily",
                        feedback='{"total_score": 95}',
                    )
                )
                db.add(
                    WeeklySnippet(
                        user_id=user.id,
                        week=target_week,
                        content="m1 weekly",
                        feedback='{"total_score": 70}',
                    )
                )
                await db.commit()

                summary = await grant_daily_achievements(
                    db,
                    target_date=target_date,
                    now=now,
                    dry_run=False,
                )

                assert set(summary["missing_definition_codes"]) == {
                    "daily_score_90",
                    "weekly_submitted",
                    "daily_rank_1",
                    "weekly_rank_1",
                    "daily_team_all_submitted",
                    "weekly_team_all_submitted",
                }
                assert summary["skipped_missing_definition_codes_count"] == 6
                assert summary["skipped_missing_definition_grants_count"] == 4
                assert summary["created_count"] == 1
                assert summary["rule_created_counts"] == {
                    "daily_submitted": 1,
                    "daily_score_90": 0,
                    "weekly_submitted": 0,
                    "daily_rank_1": 0,
                    "weekly_rank_1": 0,
                    "daily_team_all_submitted": 0,
                    "weekly_team_all_submitted": 0,
                    "daily_streak_7": 0,
                    "daily_streak_28": 0,
                    "daily_streak_100": 0,
                    "team_daily_streak_7": 0,
                    "team_daily_streak_28": 0,
                }
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_personal_streak_thresholds_and_repeat_grants(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_test_session_factory(tmp_path, "personal_streak")
        try:
            base_date = date(2026, 2, 23)
            now = datetime(2026, 2, 24, 10, 0, tzinfo=timezone(timedelta(hours=9)))

            async with SessionLocal() as db:
                users = await _seed_users_and_definitions(db)
                user = users[0]

                await _seed_daily_streak(db, user.id, base_date, 100, content_prefix="u1")
                await db.commit()

                summary = await grant_daily_achievements(db, target_date=base_date, now=now, dry_run=False)

                assert summary["rule_candidate_counts"]["daily_streak_7"] == 1
                assert summary["rule_candidate_counts"]["daily_streak_28"] == 1
                assert summary["rule_candidate_counts"]["daily_streak_100"] == 1

                ids = await _get_external_ids(db)
                prefix = f"daily:{base_date.isoformat()}:"
                assert f"{prefix}daily_streak_7:user:{user.id}" in ids
                assert f"{prefix}daily_streak_28:user:{user.id}" in ids
                assert f"{prefix}daily_streak_100:user:{user.id}" in ids

                next_target_date = base_date + timedelta(days=7)
                await _seed_daily_streak(db, user.id, next_target_date, 7, content_prefix="u1-repeat-7")
                await db.commit()

                summary_repeat = await grant_daily_achievements(
                    db,
                    target_date=next_target_date,
                    now=now + timedelta(days=7),
                    dry_run=False,
                )

                assert summary_repeat["rule_candidate_counts"]["daily_streak_7"] == 1
                assert summary_repeat["rule_candidate_counts"]["daily_streak_28"] == 0
                assert summary_repeat["rule_candidate_counts"]["daily_streak_100"] == 0

                ids_repeat = await _get_external_ids(db)
                repeat_prefix = f"daily:{next_target_date.isoformat()}:"
                assert f"{repeat_prefix}daily_streak_7:user:{user.id}" in ids_repeat
                assert f"{repeat_prefix}daily_streak_28:user:{user.id}" not in ids_repeat
                assert f"{repeat_prefix}daily_streak_100:user:{user.id}" not in ids_repeat
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_team_streak_thresholds_and_single_member_team_exclusion(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_test_session_factory(tmp_path, "team_streak")
        try:
            target_date = date(2026, 2, 23)
            now = datetime(2026, 2, 24, 10, 0, tzinfo=timezone(timedelta(hours=9)))

            async with SessionLocal() as db:
                team_a = Team(name="Team A", invite_code="TSTREAKA")
                team_b = Team(name="Team B", invite_code="TSTREAKB")
                db.add_all([team_a, team_b])
                await db.flush()

                team_a_users = [
                    User(google_sub="ta1", email="ta1@example.com", name="TA1", team_id=team_a.id),
                    User(google_sub="ta2", email="ta2@example.com", name="TA2", team_id=team_a.id),
                ]
                single_user = User(google_sub="tb1", email="tb1@example.com", name="TB1", team_id=team_b.id)
                db.add_all(team_a_users + [single_user])
                await db.flush()

                await _seed_users_and_definitions(db)

                await _seed_daily_streak(db, team_a_users[0].id, target_date, 28, content_prefix="ta1")
                await _seed_daily_streak(db, team_a_users[1].id, target_date, 28, content_prefix="ta2")
                await _seed_daily_streak(db, single_user.id, target_date, 28, content_prefix="tb1")
                await db.commit()

                summary = await grant_daily_achievements(db, target_date=target_date, now=now, dry_run=False)

                assert summary["rule_candidate_counts"]["team_daily_streak_7"] == 2
                assert summary["rule_candidate_counts"]["team_daily_streak_28"] == 2

                ids = await _get_external_ids(db)
                prefix = f"daily:{target_date.isoformat()}:"
                assert f"{prefix}team_daily_streak_7:team:{team_a.id}:user:{team_a_users[0].id}" in ids
                assert f"{prefix}team_daily_streak_7:team:{team_a.id}:user:{team_a_users[1].id}" in ids
                assert f"{prefix}team_daily_streak_28:team:{team_a.id}:user:{team_a_users[0].id}" in ids
                assert f"{prefix}team_daily_streak_28:team:{team_a.id}:user:{team_a_users[1].id}" in ids
                assert f"{prefix}team_daily_streak_7:team:{team_b.id}:user:{single_user.id}" not in ids
                assert f"{prefix}team_daily_streak_28:team:{team_b.id}:user:{single_user.id}" not in ids
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_rule_specific_reset_with_same_target_date_rerun_stability(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_test_session_factory(tmp_path, "streak_idempotency")
        try:
            target_date = date(2026, 2, 23)
            now = datetime(2026, 2, 24, 10, 0, tzinfo=timezone(timedelta(hours=9)))

            async with SessionLocal() as db:
                users = await _seed_users_and_definitions(db)
                user = users[0]
                await _seed_daily_streak(db, user.id, target_date, 7, content_prefix="u1")
                await db.commit()

                first = await grant_daily_achievements(db, target_date=target_date, now=now, dry_run=False)
                second = await grant_daily_achievements(db, target_date=target_date, now=now, dry_run=False)

                assert first["rule_candidate_counts"]["daily_streak_7"] == 1
                assert second["rule_candidate_counts"]["daily_streak_7"] == 1
                assert second["deleted_count"] == first["created_count"]

                ids = await _get_external_ids(db)
                prefix = f"daily:{target_date.isoformat()}:"
                daily_streak_ids = [
                    item for item in ids if item == f"{prefix}daily_streak_7:user:{user.id}"
                ]
                assert len(daily_streak_ids) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())
