from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app import crud_comments
from app.crud_notifications import create_comment_notifications
from app.models import Base, Comment, DailySnippet, NotificationSetting, Team, User


def _build_user(email: str, name: str, team_id: int, department: str | None = None) -> User:
    try:
        return User(email=email, name=name, team_id=team_id, department=department)
    except TypeError:
        return User(email=email, name=name, team_id=team_id)


async def _create_session_factory(tmp_path, name: str):
    db_path = tmp_path / f"{name}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_notifications_dedupe_key "
                "ON notifications(dedupe_key)"
            )
        )

    return engine, async_sessionmaker(bind=engine, expire_on_commit=False)


async def _count_notifications(db, user_id: int) -> int:
    result = await db.execute(
        text("SELECT COUNT(*) FROM notifications WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    return int(result.scalar_one())


def test_create_comment_notifications_builds_recipients_with_settings_and_dedupe(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_session_factory(tmp_path, "comment_notification_recipients")
        try:
            async with SessionLocal() as db:
                team = Team(name="A Team", invite_code="TEAM1001")
                db.add(team)
                await db.flush()

                author = _build_user("author@example.com", "author", team.id)
                actor = _build_user("actor@example.com", "actor", team.id)
                mentioned = _build_user("mentioned@example.com", "mention", team.id)
                participant = _build_user("participant@example.com", "participant", team.id)
                duplicate_1 = _build_user("dup1@example.com", "dupe", team.id)
                duplicate_2 = _build_user("dup2@example.com", "dupe", team.id)
                outsider_team = Team(name="B Team", invite_code="TEAM2001")
                db.add(outsider_team)
                await db.flush()
                outsider = _build_user("outsider@example.com", "mention", outsider_team.id)

                db.add_all(
                    [author, actor, mentioned, participant, duplicate_1, duplicate_2, outsider]
                )
                await db.flush()

                snippet = DailySnippet(
                    user_id=author.id,
                    date=date(2026, 2, 27),
                    content="daily",
                )
                db.add(snippet)
                await db.flush()

                old_comment = Comment(
                    user_id=participant.id,
                    daily_snippet_id=snippet.id,
                    content="old",
                )
                db.add(old_comment)
                await db.flush()

                new_comment = Comment(
                    user_id=actor.id,
                    daily_snippet_id=snippet.id,
                    content="hello @mention @dupe",
                )
                db.add(new_comment)
                await db.flush()

                db.add_all(
                    [
                        NotificationSetting(
                            user_id=author.id,
                            notify_post_author=True,
                            notify_mentions=False,
                            notify_participants=True,
                        ),
                        NotificationSetting(
                            user_id=mentioned.id,
                            notify_post_author=True,
                            notify_mentions=True,
                            notify_participants=True,
                        ),
                        NotificationSetting(
                            user_id=participant.id,
                            notify_post_author=True,
                            notify_mentions=True,
                            notify_participants=False,
                        ),
                    ]
                )
                await db.commit()

                await create_comment_notifications(db, new_comment)
                await create_comment_notifications(db, new_comment)

                author_count = await _count_notifications(db, author.id)
                mentioned_count = await _count_notifications(db, mentioned.id)
                participant_count = await _count_notifications(db, participant.id)
                actor_count = await _count_notifications(db, actor.id)

                assert author_count == 1
                assert mentioned_count == 1
                assert participant_count == 0
                assert actor_count == 0

                result = await db.execute(
                    text(
                        "SELECT user_id, type, dedupe_key FROM notifications "
                        "ORDER BY user_id ASC, type ASC"
                    )
                )
                rows = result.all()
                assert len(rows) == 2
                assert rows[0].type == "comment_on_my_snippet"
                assert rows[1].type == "mention_in_comment"
                assert rows[0].dedupe_key == (
                    f"comment:{new_comment.id}:recipient:{author.id}:"
                    "type:comment_on_my_snippet"
                )
                assert rows[1].dedupe_key == (
                    f"comment:{new_comment.id}:recipient:{mentioned.id}:"
                    "type:mention_in_comment"
                )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_create_comment_notifications_supports_name_department_format(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_session_factory(tmp_path, "comment_notification_name_department")
        try:
            async with SessionLocal() as db:
                team = Team(name="Dept Team", invite_code="DEPT1001")
                db.add(team)
                await db.flush()

                author = _build_user("author3@example.com", "author3", team.id)
                actor = _build_user("actor3@example.com", "actor3", team.id)
                target = _build_user("target@example.com", "김남주/건축학과", team.id)
                same_name_only = _build_user("sameonly@example.com", "김남주", team.id)
                db.add_all([author, actor, target, same_name_only])
                await db.flush()

                snippet = DailySnippet(user_id=author.id, date=date(2026, 2, 27), content="daily")
                db.add(snippet)
                await db.flush()

                comment = Comment(
                    user_id=actor.id,
                    daily_snippet_id=snippet.id,
                    content="hello @김남주/건축학과 @김남주/없는학과",
                )
                db.add(comment)
                await db.commit()

                await create_comment_notifications(db, comment)

                result = await db.execute(
                    text("SELECT user_id, type FROM notifications ORDER BY id ASC")
                )
                rows = result.all()
                assert len(rows) == 2
                assert rows[0].user_id == author.id
                assert rows[0].type == "comment_on_my_snippet"
                assert rows[1].user_id == target.id
                assert rows[1].type == "mention_in_comment"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_create_comment_notifications_skips_ambiguous_mentions(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_session_factory(tmp_path, "comment_notification_ambiguous")
        try:
            async with SessionLocal() as db:
                team = Team(name="C Team", invite_code="TEAM3001")
                db.add(team)
                await db.flush()

                author = _build_user("author2@example.com", "author2", team.id)
                actor = _build_user("actor2@example.com", "actor2", team.id)
                same_name_1 = _build_user("same1@example.com", "same", team.id)
                same_name_2 = _build_user("same2@example.com", "same", team.id)
                db.add_all([author, actor, same_name_1, same_name_2])
                await db.flush()

                snippet = DailySnippet(
                    user_id=author.id,
                    date=date(2026, 2, 27),
                    content="daily",
                )
                db.add(snippet)
                await db.flush()

                new_comment = Comment(
                    user_id=actor.id,
                    daily_snippet_id=snippet.id,
                    content="hello @same",
                )
                db.add(new_comment)
                await db.commit()

                await create_comment_notifications(db, new_comment)

                result = await db.execute(
                    text("SELECT user_id, type FROM notifications ORDER BY id ASC")
                )
                rows = result.all()
                assert len(rows) == 1
                assert rows[0].user_id == author.id
                assert rows[0].type == "comment_on_my_snippet"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_delete_comment_removes_related_notifications(tmp_path):
    async def scenario() -> None:
        engine, SessionLocal = await _create_session_factory(tmp_path, "comment_delete_notification_cleanup")
        try:
            async with SessionLocal() as db:
                team = Team(name="Cleanup Team", invite_code="CLN1001")
                db.add(team)
                await db.flush()

                actor = _build_user("actor-clean@example.com", "actor-clean", team.id)
                recipient = _build_user("recipient-clean@example.com", "recipient-clean", team.id)
                db.add_all([actor, recipient])
                await db.flush()

                snippet = DailySnippet(
                    user_id=recipient.id,
                    date=date(2026, 2, 28),
                    content="cleanup target",
                )
                db.add(snippet)
                await db.flush()

                comment = Comment(
                    user_id=actor.id,
                    daily_snippet_id=snippet.id,
                    content="hello cleanup",
                )
                db.add(comment)
                await db.commit()

                await create_comment_notifications(db, comment)

                before = await db.execute(
                    text("SELECT COUNT(*) FROM notifications WHERE comment_id = :comment_id"),
                    {"comment_id": comment.id},
                )
                assert int(before.scalar_one()) == 1

                loaded_comment = await crud_comments.get_comment_by_id(db, comment.id)
                assert loaded_comment is not None

                await crud_comments.delete_comment(db, loaded_comment)

                after_comment = await crud_comments.get_comment_by_id(db, comment.id)
                assert after_comment is None

                after_notifications = await db.execute(
                    text("SELECT COUNT(*) FROM notifications WHERE comment_id = :comment_id"),
                    {"comment_id": comment.id},
                )
                assert int(after_notifications.scalar_one()) == 0
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_create_comment_triggers_notification_fail_safe(monkeypatch):
    async def scenario() -> None:
        captured = {"called": False}

        class FakeDB:
            def __init__(self):
                self.added = []

            def add(self, obj):
                self.added.append(obj)
                if getattr(obj, "id", None) is None:
                    obj.id = 999

            async def commit(self):
                return None

        async def fake_create_comment_notifications(db, comment):
            captured["called"] = True
            raise RuntimeError("notification error")

        async def fake_get_comment_by_id(db, comment_id):
            return SimpleNamespace(id=comment_id, user=None)

        monkeypatch.setattr(
            crud_comments,
            "create_comment_notifications",
            fake_create_comment_notifications,
        )
        monkeypatch.setattr(crud_comments, "get_comment_by_id", fake_get_comment_by_id)

        db = FakeDB()
        created = await crud_comments.create_comment(
            db,
            user_id=1,
            content="hello",
            daily_snippet_id=5,
        )

        assert captured["called"] is True
        assert created.id == 999

    asyncio.run(scenario())


def test_create_comment_persists_professor_type(monkeypatch):
    async def scenario() -> None:
        class FakeDB:
            def __init__(self):
                self.added = []

            def add(self, obj):
                self.added.append(obj)
                if getattr(obj, "id", None) is None:
                    obj.id = 1001

            async def commit(self):
                return None

        async def fake_create_comment_notifications(db, comment):
            return None

        async def fake_get_comment_by_id(db, comment_id):
            comment = next(item for item in db.added if getattr(item, "id", None) == comment_id)
            return SimpleNamespace(
                id=comment.id,
                user_id=comment.user_id,
                content=comment.content,
                daily_snippet_id=comment.daily_snippet_id,
                weekly_snippet_id=comment.weekly_snippet_id,
                comment_type=comment.comment_type,
                user=None,
            )

        monkeypatch.setattr(
            crud_comments,
            "create_comment_notifications",
            fake_create_comment_notifications,
        )
        monkeypatch.setattr(crud_comments, "get_comment_by_id", fake_get_comment_by_id)

        db = FakeDB()
        created = await crud_comments.create_comment(
            db,
            user_id=1,
            content="professor message",
            daily_snippet_id=5,
            comment_type="professor",
        )

        assert created.id == 1001
        assert created.comment_type == "professor"

    asyncio.run(scenario())
