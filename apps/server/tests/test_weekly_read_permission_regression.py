import asyncio
from datetime import date
import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import crud
from app.routers import snippet_utils as _snippet_utils
from app.routers import weekly_snippets


async def _async_true(*args, **kwargs):
    return True


async def _async_false(*args, **kwargs):
    return False


class DummyDB:
    pass


class WeeklySnippetStub:
    def __init__(self, snippet_id: int, owner_id: int, week: date):
        self.id = snippet_id
        self.user_id = owner_id
        self.week = week


def _make_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/weekly-snippets/1",
        "headers": [],
    }
    return Request(scope)


def test_weekly_get_allows_same_team_member_for_gcs(monkeypatch):
    viewer = SimpleNamespace(id=2, team_id=10, roles=["gcs"])
    owner = SimpleNamespace(id=1, team_id=10)
    snippet = WeeklySnippetStub(snippet_id=1, owner_id=owner.id, week=date(2026, 2, 16))

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(_snippet_utils, "can_read_snippet", _async_true)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.get_weekly_snippet)(
            snippet_id=snippet.id,
            request=_make_request(),
            db=DummyDB(),
        )
    )

    assert result is snippet
    assert hasattr(result, "editable")
    assert result.editable is False


def test_weekly_get_denies_non_owner_other_team(monkeypatch):
    viewer = SimpleNamespace(id=2, team_id=20, roles=["가천대학교"])
    owner = SimpleNamespace(id=1, team_id=10)
    snippet = WeeklySnippetStub(snippet_id=1, owner_id=owner.id, week=date(2026, 2, 16))

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(_snippet_utils, "can_read_snippet", _async_false)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.get_weekly_snippet)(
                snippet_id=snippet.id,
                request=_make_request(),
                db=DummyDB(),
            )
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied"


def test_weekly_get_allows_professor_other_team(monkeypatch):
    viewer = SimpleNamespace(id=2, team_id=20, roles=["교수"])
    owner = SimpleNamespace(id=1, team_id=10)
    snippet = WeeklySnippetStub(snippet_id=2, owner_id=owner.id, week=date(2026, 2, 23))

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(_snippet_utils, "can_read_snippet", _async_true)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.get_weekly_snippet)(
            snippet_id=snippet.id,
            request=_make_request(),
            db=DummyDB(),
        )
    )

    assert result is snippet
    assert result.editable is False
