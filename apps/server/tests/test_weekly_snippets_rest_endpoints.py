import asyncio
from datetime import date, datetime, timedelta, timezone
import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import crud, schemas
from app.models import Base, Team, User, UserTeamHistory, WeeklySnippet
from app.routers import snippet_access, snippet_utils as _snippet_utils
from app.routers import weekly_snippets


async def _async_true(*args, **kwargs):
    return True


async def _async_false(*args, **kwargs):
    return False


def _make_request(
    path: str,
    method: str,
    headers: dict[str, str] | None = None,
) -> Request:
    encoded_headers = [
        (key.lower().encode("utf-8"), value.encode("utf-8"))
        for key, value in (headers or {}).items()
    ]

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": encoded_headers,
            "query_string": b"",
            "session": {},
        },
        receive=receive,
    )


def _weekly_snippet(snippet_id: int, user_id: int, week: date, content: str = "weekly"):
    return SimpleNamespace(
        id=snippet_id,
        user_id=user_id,
        week=week,
        content=content,
        feedback=None,
        playbook=None,
        created_at=datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc),
        user=None,
        editable=False,
    )


def test_weekly_page_data_with_id_success(monkeypatch):
    request = _make_request(path="/weekly-snippets/page-data", method="GET")
    viewer = SimpleNamespace(id=1, team_id=10)
    owner = SimpleNamespace(id=2, team_id=10)
    target_week = date(2026, 2, 16)
    candidate = _weekly_snippet(600, owner.id, target_week)
    prev_item = _weekly_snippet(590, owner.id, target_week - timedelta(days=7))
    next_item = _weekly_snippet(610, owner.id, target_week + timedelta(days=7))

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return candidate

    async def fake_get_user_by_id(db, user_id):
        return owner

    async def fake_list_weekly_snippets(db, viewer, limit, offset, order, from_week, to_week, q, scope):
        if order == "desc" and to_week == target_week - timedelta(days=7):
            return [prev_item], 1
        if order == "asc" and from_week == target_week + timedelta(days=7):
            return [next_item], 1
        return [], 0

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: date(2026, 2, 23))
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(crud, "list_weekly_snippets", fake_list_weekly_snippets)
    monkeypatch.setattr(_snippet_utils, "can_read_snippet", _async_true)
    monkeypatch.setattr(snippet_access, "can_read_snippet", _async_true)
    monkeypatch.setattr(_snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: False)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.get_weekly_snippet_page_data)(
            request=request,
            db=object(),
            id=600,
        )
    )

    assert result["snippet"].id == 600
    assert result["read_only"] is True
    assert result["prev_id"] == 590
    assert result["next_id"] == 610


def test_weekly_page_data_without_id_uses_current_week(monkeypatch):
    request = _make_request(path="/weekly-snippets/page-data", method="GET")
    viewer = SimpleNamespace(id=1, team_id=10)
    week = date(2026, 2, 23)
    item = _weekly_snippet(700, viewer.id, week)

    calls = []

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_list_weekly_snippets(db, viewer, limit, offset, order, from_week, to_week, q, scope):
        calls.append((order, from_week, to_week))
        if order == "desc" and from_week == week and to_week == week:
            return [item], 1
        return [], 0

    async def fake_get_user_by_id(db, user_id):
        return viewer

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: week)
    monkeypatch.setattr(crud, "list_weekly_snippets", fake_list_weekly_snippets)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(_snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.get_weekly_snippet_page_data)(
            request=request,
            db=object(),
            id=None,
        )
    )

    assert result["snippet"].id == 700
    assert result["read_only"] is False
    assert calls[0] == ("desc", week, week)


def test_weekly_professor_page_data_requires_professor_role(monkeypatch):
    async def fake_get_viewer(request_arg, db):
        return SimpleNamespace(id=1, roles=["user"])

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.get_weekly_snippet_page_data_for_professor)(
                request=_make_request("/weekly-snippets/professor/page-data", "GET"),
                student_user_id=10,
                db=object(),
                id=None,
                week=None,
            )
        )

    assert exc_info.value.status_code == 403


def test_weekly_professor_page_data_invalid_week_returns_400(monkeypatch):
    async def fake_get_viewer(request_arg, db):
        return SimpleNamespace(id=1, roles=["교수"])

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.get_weekly_snippet_page_data_for_professor)(
                request=_make_request("/weekly-snippets/professor/page-data", "GET"),
                student_user_id=10,
                db=object(),
                id=None,
                week="not-a-week",
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid week parameter"


def test_weekly_professor_page_data_ignores_other_student_snippet_id(monkeypatch):
    request = _make_request(path="/weekly-snippets/professor/page-data", method="GET")
    viewer = SimpleNamespace(id=1, roles=["교수"])

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return _weekly_snippet(snippet_id, user_id=999, week=date(2026, 3, 9))

    async def fake_build_page_data(**kwargs):
        resolved = await kwargs["get_snippet_by_id"](77)
        assert resolved is None
        return {
            "snippet": None,
            "read_only": True,
            "prev_id": None,
            "next_id": None,
        }

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda _req: datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: date(2026, 3, 9))
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(_snippet_utils, "build_snippet_page_data", fake_build_page_data)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.get_weekly_snippet_page_data_for_professor)(
            request=request,
            student_user_id=10,
            db=object(),
            id=77,
            week=None,
        )
    )

    assert result["read_only"] is True


def test_weekly_get_not_found_returns_404(monkeypatch):
    async def fake_get_viewer(request_arg, db):
        return SimpleNamespace(id=1, team_id=1)

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return None

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.get_weekly_snippet)(
                snippet_id=1,
                request=_make_request("/weekly-snippets/1", "GET"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_weekly_get_access_denied_returns_403(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=2, team_id=2)
    snippet = _weekly_snippet(1, owner.id, date(2026, 2, 23))

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(weekly_snippets, "_can_read", _async_false)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.get_weekly_snippet)(
                snippet_id=1,
                request=_make_request("/weekly-snippets/1", "GET"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_weekly_get_success(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=10)
    owner = SimpleNamespace(id=2, team_id=10)
    snippet = _weekly_snippet(1, owner.id, date(2026, 2, 23))

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(weekly_snippets, "_can_read", _async_true)
    monkeypatch.setattr(_snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.get_weekly_snippet)(
            snippet_id=1,
            request=_make_request("/weekly-snippets/1", "GET"),
            db=object(),
        )
    )

    assert result is snippet
    assert result.editable is True


def test_weekly_list_with_id_not_found_returns_404(monkeypatch):
    async def fake_get_viewer(request_arg, db):
        return SimpleNamespace(id=1, team_id=1)

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return None

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.list_weekly_snippets)(
                request=_make_request("/weekly-snippets", "GET"),
                db=object(),
                limit=20,
                offset=0,
                order="desc",
                from_week=None,
                to_week=None,
                id=99,
                q=None,
                scope="own",
            )
        )

    assert exc_info.value.status_code == 404


def test_weekly_list_success_default_week(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    item = _weekly_snippet(22, viewer.id, date(2026, 2, 23))

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_list_weekly_snippets(db, viewer, limit, offset, order, from_week, to_week, q, scope):
        assert from_week == date(2026, 2, 23)
        assert to_week == date(2026, 2, 23)
        return [item], 1

    async def fake_get_user_by_id(db, user_id):
        return viewer

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: date(2026, 2, 23))
    monkeypatch.setattr(crud, "list_weekly_snippets", fake_list_weekly_snippets)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(_snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.list_weekly_snippets)(
            request=_make_request("/weekly-snippets", "GET"),
            db=object(),
            limit=20,
            offset=0,
            order="desc",
            from_week=None,
            to_week=None,
            id=None,
            q=None,
            scope="own",
        )
    )

    assert result["total"] == 1
    assert result["items"][0].id == 22


def test_weekly_create_success(monkeypatch):
    viewer = SimpleNamespace(id=5, team_id=1)
    created = _weekly_snippet(44, viewer.id, date(2026, 2, 23), content="weekly new")

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_upsert_weekly_snippet(db, user_id, week, content, playbook=None, feedback=None):
        assert user_id == 5
        assert week == date(2026, 2, 23)
        assert content == "weekly new"
        return created

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: date(2026, 2, 23))
    monkeypatch.setattr(crud, "upsert_weekly_snippet", fake_upsert_weekly_snippet)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.create_weekly_snippet)(
            payload=schemas.WeeklySnippetCreate(content="weekly new"),
            request=_make_request("/weekly-snippets", "POST"),
            db=object(),
        )
    )

    assert result.id == 44
    assert result.content == "weekly new"


def test_weekly_update_not_editable_returns_403(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=2, team_id=1)
    snippet = _weekly_snippet(88, owner.id, date(2026, 2, 16), content="old")

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(_snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.update_weekly_snippet)(
                snippet_id=88,
                payload=schemas.WeeklySnippetUpdate(content="new"),
                request=_make_request("/weekly-snippets/88", "PUT"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not editable"


def test_weekly_update_success(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=1, team_id=1)
    snippet = _weekly_snippet(88, owner.id, date(2026, 2, 23), content="old")

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    async def fake_update_weekly_snippet(db, snippet, content, playbook=None, feedback=None):
        snippet.content = content
        return snippet

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(_snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(crud, "update_weekly_snippet", fake_update_weekly_snippet)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.update_weekly_snippet)(
            snippet_id=88,
            payload=schemas.WeeklySnippetUpdate(content="new"),
            request=_make_request("/weekly-snippets/88", "PUT"),
            db=object(),
        )
    )

    assert result.content == "new"


def test_weekly_delete_not_found_returns_404(monkeypatch):
    async def fake_get_viewer(request_arg, db):
        return SimpleNamespace(id=1, team_id=1)

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return None

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.delete_weekly_snippet)(
                snippet_id=1,
                request=_make_request("/weekly-snippets/1", "DELETE"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_weekly_delete_success(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=1, team_id=1)
    snippet = _weekly_snippet(1, owner.id, date(2026, 2, 23), content="x")
    deleted: dict[str, int] = {}

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    async def fake_delete_weekly_snippet(db, snippet):
        deleted["id"] = snippet.id

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(_snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(crud, "delete_weekly_snippet", fake_delete_weekly_snippet)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.delete_weekly_snippet)(
            snippet_id=1,
            request=_make_request("/weekly-snippets/1", "DELETE"),
            db=object(),
        )
    )

    assert result == {"message": "Snippet deleted"}
    assert deleted["id"] == 1


def test_weekly_list_team_scope_without_team_falls_back_to_own_items(tmp_path):
    async def scenario() -> None:
        db_path = tmp_path / "weekly_scope_fallback.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

        try:
            async with SessionLocal() as db:
                team = Team(name="Team A", invite_code="TEAMA001")
                db.add(team)
                await db.flush()

                viewer = User(email="viewer@example.com", name="viewer", team_id=None, roles=["gcs"])
                teammate = User(email="teammate@example.com", name="teammate", team_id=team.id)
                db.add_all([viewer, teammate])
                await db.flush()

                own = WeeklySnippet(user_id=viewer.id, week=date(2026, 2, 23), content="own weekly")
                others = WeeklySnippet(user_id=teammate.id, week=date(2026, 2, 23), content="team weekly")
                db.add_all([own, others])
                await db.commit()

                items, total = await crud.list_weekly_snippets(
                    db,
                    viewer=viewer,
                    limit=20,
                    offset=0,
                    order="desc",
                    from_week=None,
                    to_week=None,
                    q=None,
                    scope="team",
                )

                assert total == 1
                assert [item.user_id for item in items] == [viewer.id]
                assert items[0].content == "own weekly"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_weekly_list_team_scope_with_gcs_role_returns_same_team_only(tmp_path):
    async def scenario() -> None:
        db_path = tmp_path / "weekly_scope_gcs_team_only.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

        try:
            async with SessionLocal() as db:
                team_a = Team(name="Team A", invite_code="TEAMWGA1")
                team_b = Team(name="Team B", invite_code="TEAMWGB1")
                db.add_all([team_a, team_b])
                await db.flush()

                viewer = User(email="gcs-weekly@example.com", name="gcs", team_id=team_a.id, roles=["gcs"])
                teammate = User(email="teammate-weekly@example.com", name="teammate", team_id=team_a.id)
                other_team = User(email="other-weekly@example.com", name="other", team_id=team_b.id)
                db.add_all([viewer, teammate, other_team])
                await db.flush()

                snippet_week = date(2026, 2, 23)
                joined = datetime(2026, 1, 1, tzinfo=timezone.utc)
                histories = [
                    UserTeamHistory(user_id=viewer.id, team_id=team_a.id, joined_at=joined),
                    UserTeamHistory(user_id=teammate.id, team_id=team_a.id, joined_at=joined),
                    UserTeamHistory(user_id=other_team.id, team_id=team_b.id, joined_at=joined),
                ]
                db.add_all(histories)
                snippets = [
                    WeeklySnippet(user_id=viewer.id, week=snippet_week, content="own weekly"),
                    WeeklySnippet(user_id=teammate.id, week=snippet_week, content="team-a weekly"),
                    WeeklySnippet(user_id=other_team.id, week=snippet_week, content="team-b weekly"),
                ]
                db.add_all(snippets)
                await db.commit()

                items, total = await crud.list_weekly_snippets(
                    db,
                    viewer=viewer,
                    limit=20,
                    offset=0,
                    order="desc",
                    from_week=None,
                    to_week=None,
                    q=None,
                    scope="team",
                )

                assert total == 2
                assert {item.user_id for item in items} == {viewer.id, teammate.id}
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_weekly_list_team_scope_with_privileged_role_uses_team_history(tmp_path):
    """교수도 팀피드에서 자신의 팀(UserTeamHistory 기준)만 볼 수 있다."""
    async def scenario() -> None:
        db_path = tmp_path / "weekly_scope_privileged.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

        try:
            async with SessionLocal() as db:
                team_a = Team(name="Team A", invite_code="TEAMWA01")
                team_b = Team(name="Team B", invite_code="TEAMWB01")
                db.add_all([team_a, team_b])
                await db.flush()

                # 교수는 team_a에 소속 (UserTeamHistory)
                viewer = User(email="prof-weekly@example.com", name="professor", team_id=None, roles=["교수"])
                student_a = User(email="weekly-a@example.com", name="student-a", team_id=team_a.id)
                student_b = User(email="weekly-b@example.com", name="student-b", team_id=team_b.id)
                db.add_all([viewer, student_a, student_b])
                await db.flush()

                snippet_week = date(2026, 2, 23)
                db.add_all([
                    UserTeamHistory(user_id=viewer.id, team_id=team_a.id, joined_at=datetime(2026, 1, 1)),
                    UserTeamHistory(user_id=student_a.id, team_id=team_a.id, joined_at=datetime(2026, 1, 1)),
                    UserTeamHistory(user_id=student_b.id, team_id=team_b.id, joined_at=datetime(2026, 1, 1)),
                ])

                snippets = [
                    WeeklySnippet(user_id=viewer.id, week=snippet_week, content="prof weekly"),
                    WeeklySnippet(user_id=student_a.id, week=snippet_week, content="team-a weekly"),
                    WeeklySnippet(user_id=student_b.id, week=snippet_week, content="team-b weekly"),
                ]
                db.add_all(snippets)
                await db.commit()

                # 팀피드: 교수와 같은 팀(team_a)인 student_a만 보여야 함
                items, total = await crud.list_weekly_snippets(
                    db,
                    viewer=viewer,
                    limit=20,
                    offset=0,
                    order="desc",
                    from_week=None,
                    to_week=None,
                    q=None,
                    scope="team",
                )

                assert total == 2
                assert {item.user_id for item in items} == {viewer.id, student_a.id}

                own_items, own_total = await crud.list_weekly_snippets(
                    db,
                    viewer=viewer,
                    limit=20,
                    offset=0,
                    order="desc",
                    from_week=None,
                    to_week=None,
                    q=None,
                    scope="own",
                )
                assert own_total == 1
                assert [item.user_id for item in own_items] == [viewer.id]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
