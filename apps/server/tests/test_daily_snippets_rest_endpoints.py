import asyncio
from datetime import date, datetime, timedelta, timezone
import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import crud, schemas
from app.routers import daily_snippets, snippet_utils


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


def _daily_snippet(snippet_id: int, user_id: int, snippet_date: date, content: str = "content"):
    return SimpleNamespace(
        id=snippet_id,
        user_id=user_id,
        date=snippet_date,
        content=content,
        feedback=None,
        playbook=None,
        created_at=datetime(2026, 2, 27, 14, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 27, 14, 0, tzinfo=timezone.utc),
        user=None,
        comments_count=0,
        editable=False,
    )


def test_daily_page_data_with_id_success_sets_navigation(monkeypatch):
    request = _make_request(path="/daily-snippets/page-data", method="GET")
    viewer = SimpleNamespace(id=1, team_id=10)
    owner = SimpleNamespace(id=2, team_id=10)
    candidate = _daily_snippet(200, owner.id, date(2026, 2, 26))
    prev_item = _daily_snippet(199, owner.id, date(2026, 2, 25))
    next_item = _daily_snippet(201, owner.id, date(2026, 2, 27))

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        assert snippet_id == 200
        return candidate

    async def fake_get_user_by_id(db, user_id):
        return owner

    async def fake_list_daily_snippets(db, viewer, limit, offset, order, from_date, to_date, q, scope):
        if order == "desc" and to_date == candidate.date - timedelta(days=1):
            return [prev_item], 1
        if order == "asc" and from_date == candidate.date + timedelta(days=1):
            return [next_item], 1
        return [], 0

    from datetime import timedelta

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 14, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: date(2026, 2, 27))
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(crud, "list_daily_snippets", fake_list_daily_snippets)
    monkeypatch.setattr(snippet_utils, "can_read_snippet", lambda _viewer, _owner: True)
    monkeypatch.setattr(snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: False)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.get_daily_snippet_page_data)(
            request=request,
            db=object(),
            id=200,
        )
    )

    assert result["snippet"].id == 200
    assert result["read_only"] is True
    assert result["prev_id"] == 199
    assert result["next_id"] == 201


def test_daily_page_data_without_id_uses_today_own_scope(monkeypatch):
    request = _make_request(path="/daily-snippets/page-data", method="GET")
    viewer = SimpleNamespace(id=1, team_id=10)
    today = date(2026, 2, 27)
    today_item = _daily_snippet(300, viewer.id, today)

    calls: list[tuple[str, date | None, date | None]] = []

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_list_daily_snippets(db, viewer, limit, offset, order, from_date, to_date, q, scope):
        calls.append((order, from_date, to_date))
        if order == "desc" and from_date == today and to_date == today:
            return [today_item], 1
        return [], 0

    async def fake_get_user_by_id(db, user_id):
        return viewer

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 14, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: today)
    monkeypatch.setattr(crud, "list_daily_snippets", fake_list_daily_snippets)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.get_daily_snippet_page_data)(
            request=request,
            db=object(),
            id=None,
        )
    )

    assert result["snippet"].id == 300
    assert result["read_only"] is False
    assert calls[0] == ("desc", today, today)


def test_daily_get_snippet_not_found_returns_404(monkeypatch):
    async def fake_get_viewer(request_arg, db):
        return SimpleNamespace(id=1, team_id=1)

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return None

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(daily_snippets.get_daily_snippet)(
                snippet_id=123,
                request=_make_request("/daily-snippets/123", "GET"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Snippet not found"


def test_daily_get_snippet_access_denied_returns_403(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=2, team_id=2)
    snippet = _daily_snippet(123, owner.id, date(2026, 2, 27))

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(snippet_utils, "can_read_snippet", lambda _viewer, _owner: False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(daily_snippets.get_daily_snippet)(
                snippet_id=123,
                request=_make_request("/daily-snippets/123", "GET"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_daily_get_snippet_success(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=10)
    owner = SimpleNamespace(id=2, team_id=10)
    snippet = _daily_snippet(123, owner.id, date(2026, 2, 27))

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(snippet_utils, "can_read_snippet", lambda _viewer, _owner: True)
    monkeypatch.setattr(snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.get_daily_snippet)(
            snippet_id=123,
            request=_make_request("/daily-snippets/123", "GET"),
            db=object(),
        )
    )

    assert result is snippet
    assert result.editable is True


def test_daily_list_with_id_not_found_returns_404(monkeypatch):
    async def fake_get_viewer(request_arg, db):
        return SimpleNamespace(id=1, team_id=1)

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return None

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(daily_snippets.list_daily_snippets)(
                request=_make_request("/daily-snippets", "GET"),
                db=object(),
                limit=20,
                offset=0,
                order="desc",
                from_date=None,
                to_date=None,
                id=999,
                q=None,
                scope="own",
            )
        )

    assert exc_info.value.status_code == 404


def test_daily_list_success_default_today(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    item = _daily_snippet(321, viewer.id, date(2026, 2, 27))

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_list_daily_snippets(db, viewer, limit, offset, order, from_date, to_date, q, scope):
        assert from_date == date(2026, 2, 27)
        assert to_date == date(2026, 2, 27)
        assert scope == "own"
        return [item], 1

    async def fake_get_user_by_id(db, user_id):
        return viewer

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 14, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: date(2026, 2, 27))
    monkeypatch.setattr(crud, "list_daily_snippets", fake_list_daily_snippets)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.list_daily_snippets)(
            request=_make_request("/daily-snippets", "GET"),
            db=object(),
            limit=20,
            offset=0,
            order="desc",
            from_date=None,
            to_date=None,
            id=None,
            q=None,
            scope="own",
        )
    )

    assert result["total"] == 1
    assert result["items"][0].id == 321


def test_daily_create_success(monkeypatch):
    viewer = SimpleNamespace(id=5, team_id=1)
    created = _daily_snippet(400, viewer.id, date(2026, 2, 27), content="new content")

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_upsert_daily_snippet(db, user_id, snippet_date, content, playbook=None, feedback=None):
        assert user_id == 5
        assert snippet_date == date(2026, 2, 27)
        assert content == "new content"
        return created

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 14, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: date(2026, 2, 27))
    monkeypatch.setattr(crud, "upsert_daily_snippet", fake_upsert_daily_snippet)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.create_daily_snippet)(
            request=_make_request("/daily-snippets", "POST"),
            payload=schemas.DailySnippetCreate(content="new content"),
            db=object(),
        )
    )

    assert result.id == 400
    assert result.content == "new content"


def test_daily_update_not_editable_returns_403(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=2, team_id=1)
    snippet = _daily_snippet(777, owner.id, date(2026, 2, 26), content="old")

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(daily_snippets.update_daily_snippet)(
                snippet_id=777,
                payload=schemas.DailySnippetUpdate(content="new"),
                request=_make_request("/daily-snippets/777", "PUT"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not editable"


def test_daily_update_success(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=1, team_id=1)
    snippet = _daily_snippet(777, owner.id, date(2026, 2, 27), content="old")

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    async def fake_update_daily_snippet(db, snippet, content, playbook=None, feedback=None):
        snippet.content = content
        return snippet

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(crud, "update_daily_snippet", fake_update_daily_snippet)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.update_daily_snippet)(
            snippet_id=777,
            payload=schemas.DailySnippetUpdate(content="new"),
            request=_make_request("/daily-snippets/777", "PUT"),
            db=object(),
        )
    )

    assert result.content == "new"


def test_daily_delete_not_found_returns_404(monkeypatch):
    async def fake_get_viewer(request_arg, db):
        return SimpleNamespace(id=1, team_id=1)

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return None

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(daily_snippets.delete_daily_snippet)(
                snippet_id=1,
                request=_make_request("/daily-snippets/1", "DELETE"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_daily_delete_success(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=1, team_id=1)
    snippet = _daily_snippet(1, owner.id, date(2026, 2, 27), content="x")
    deleted: dict[str, int] = {}

    async def fake_get_viewer(request_arg, db):
        return viewer

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return snippet

    async def fake_get_user_by_id(db, user_id):
        return owner

    async def fake_delete_daily_snippet(db, snippet):
        deleted["id"] = snippet.id

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(snippet_utils, "is_snippet_editable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(crud, "delete_daily_snippet", fake_delete_daily_snippet)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.delete_daily_snippet)(
            snippet_id=1,
            request=_make_request("/daily-snippets/1", "DELETE"),
            db=object(),
        )
    )

    assert result == {"message": "Snippet deleted"}
    assert deleted["id"] == 1
