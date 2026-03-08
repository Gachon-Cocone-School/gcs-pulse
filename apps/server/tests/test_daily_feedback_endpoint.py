import asyncio
from datetime import date, datetime, timezone
import inspect
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import crud
from app.routers import daily_snippets
from app.routers import snippet_utils


class DummyDB:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True

    async def refresh(self, _snippet):
        return None


class DailySnippetStub:
    def __init__(self, target_date: date, content: str = "existing daily content"):
        self.id = 1
        self.user_id = 1
        self.date = target_date
        self.content = content
        self.playbook = "existing daily playbook"
        self.feedback = None


def _make_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/daily-snippets/feedback",
        "query_string": b"",
        "headers": [],
    }
    return Request(scope)


def test_daily_feedback_endpoint_contract_and_prompt_defaults(monkeypatch):
    target_date = date(2026, 2, 23)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()
    snippet = DailySnippetStub(target_date, content="raw daily content")
    db = DummyDB()

    captured: dict[str, str | None] = {}

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_daily_snippet_by_user_and_date(db, user_id, snippet_date):
        return snippet

    async def fake_generate_feedback_with_ai(
        snippet_content,
        playbook_content,
        copilot,
        prompt_name="daily_feedback.md",
        snippet_label="Daily Snippet",
        profile_context=None,
        **_kwargs,
    ):
        captured["snippet_content"] = snippet_content
        captured["playbook_content"] = playbook_content
        captured["prompt_name"] = prompt_name
        captured["snippet_label"] = snippet_label
        captured["profile_context"] = profile_context
        return json.dumps(
            {
                "total_score": 81,
                "scores": {"record_completeness": {"score": 12, "max_score": 15}},
                "playbook_update_markdown": "## refreshed daily playbook",
            }
        )

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: target_date)
    monkeypatch.setattr(crud, "get_daily_snippet_by_user_and_date", fake_get_daily_snippet_by_user_and_date)
    monkeypatch.setattr(snippet_utils, "generate_feedback_with_ai", fake_generate_feedback_with_ai)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.generate_daily_snippet_feedback)(
            request=_make_request(),
            db=db,
            copilot=object(),
        )
    )

    assert result.date == target_date
    assert result.feedback is not None
    assert captured["snippet_content"] == "raw daily content"
    assert captured["playbook_content"] == "existing daily playbook"
    assert captured["profile_context"] is not None
    assert captured["prompt_name"] == "daily_feedback.md"
    assert captured["snippet_label"] == "Daily Snippet"
    assert snippet.feedback == result.feedback
    assert db.committed is True


def test_daily_feedback_endpoint_empty_content_returns_400(monkeypatch):
    target_date = date(2026, 2, 23)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_daily_snippet_by_user_and_date(db, user_id, snippet_date):
        return DailySnippetStub(target_date, content="   ")

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: target_date)
    monkeypatch.setattr(crud, "get_daily_snippet_by_user_and_date", fake_get_daily_snippet_by_user_and_date)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(daily_snippets.generate_daily_snippet_feedback)(
                request=_make_request(),
                db=DummyDB(),
                copilot=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "content is required"


def test_daily_feedback_endpoint_missing_snippet_returns_400(monkeypatch):
    target_date = date(2026, 2, 23)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_daily_snippet_by_user_and_date(db, user_id, snippet_date):
        return None

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: target_date)
    monkeypatch.setattr(crud, "get_daily_snippet_by_user_and_date", fake_get_daily_snippet_by_user_and_date)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(daily_snippets.generate_daily_snippet_feedback)(
                request=_make_request(),
                db=DummyDB(),
                copilot=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "content is required"


def test_daily_feedback_endpoint_invalid_json_soft_fallback(monkeypatch):
    target_date = date(2026, 2, 23)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()
    snippet = DailySnippetStub(target_date, content="raw daily content")
    db = DummyDB()

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_daily_snippet_by_user_and_date(db, user_id, snippet_date):
        return snippet

    async def fake_generate_feedback_with_ai(
        snippet_content,
        playbook_content,
        copilot,
        prompt_name="daily_feedback.md",
        snippet_label="Daily Snippet",
        profile_context=None,
        **_kwargs,
    ):
        return "not-a-json"

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: target_date)
    monkeypatch.setattr(crud, "get_daily_snippet_by_user_and_date", fake_get_daily_snippet_by_user_and_date)
    monkeypatch.setattr(snippet_utils, "generate_feedback_with_ai", fake_generate_feedback_with_ai)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.generate_daily_snippet_feedback)(
            request=_make_request(),
            db=db,
            copilot=object(),
        )
    )

    assert result.date == target_date
    assert result.feedback is None
    assert snippet.feedback is None
    assert db.committed is True
