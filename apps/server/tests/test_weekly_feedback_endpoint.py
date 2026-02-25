import asyncio
from datetime import date, datetime, timezone
import inspect
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import crud
from app.routers import snippet_utils as _snippet_utils
from app.routers import weekly_snippets


class DummyDB:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True

    async def refresh(self, _snippet):
        return None


class WeeklySnippetStub:
    def __init__(self, target_week: date, content: str = "existing weekly content"):
        self.id = 2
        self.user_id = 1
        self.week = target_week
        self.content = content
        self.playbook = "existing weekly playbook"
        self.feedback = None


def _make_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/weekly-snippets/feedback",
        "query_string": b"",
        "headers": [],
    }
    return Request(scope)


def test_weekly_feedback_endpoint_contract_and_prompt_defaults(monkeypatch):
    target_week = date(2026, 2, 16)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()
    snippet = WeeklySnippetStub(target_week, content="raw weekly content")
    db = DummyDB()

    captured: dict[str, str | None] = {}

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_user_and_week(db, user_id, week):
        return snippet

    async def fake_generate_feedback_with_ai(
        daily_snippet_content,
        organized_content,
        playbook_content,
        copilot,
        prompt_name="daily_feedback.md",
        snippet_label="Daily Snippet",
    ):
        captured["daily_snippet_content"] = daily_snippet_content
        captured["organized_content"] = organized_content
        captured["playbook_content"] = playbook_content
        captured["prompt_name"] = prompt_name
        captured["snippet_label"] = snippet_label
        return json.dumps(
            {
                "total_score": 89,
                "scores": {"record_completeness": {"score": 13, "max_score": 15}},
                "playbook_update_markdown": "## refreshed weekly playbook",
            }
        )

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: target_week)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_user_and_week", fake_get_weekly_snippet_by_user_and_week)
    monkeypatch.setattr(_snippet_utils, "generate_feedback_with_ai", fake_generate_feedback_with_ai)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.generate_weekly_snippet_feedback)(
            request=_make_request(),
            db=db,
            copilot=object(),
        )
    )

    assert result.week == target_week
    assert result.feedback is not None
    assert captured["daily_snippet_content"] == "raw weekly content"
    assert captured["organized_content"] == "raw weekly content"
    assert captured["playbook_content"] == "existing weekly playbook"
    assert captured["prompt_name"] == "weekly_feedback.md"
    assert captured["snippet_label"] == "Weekly Snippet"
    assert snippet.feedback == result.feedback
    assert db.committed is True


def test_weekly_feedback_endpoint_empty_content_returns_400(monkeypatch):
    target_week = date(2026, 2, 16)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_user_and_week(db, user_id, week):
        return WeeklySnippetStub(target_week, content="\n\t ")

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: target_week)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_user_and_week", fake_get_weekly_snippet_by_user_and_week)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.generate_weekly_snippet_feedback)(
                request=_make_request(),
                db=DummyDB(),
                copilot=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "content is required"


def test_weekly_feedback_endpoint_missing_snippet_returns_400(monkeypatch):
    target_week = date(2026, 2, 16)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_user_and_week(db, user_id, week):
        return None

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: target_week)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_user_and_week", fake_get_weekly_snippet_by_user_and_week)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(weekly_snippets.generate_weekly_snippet_feedback)(
                request=_make_request(),
                db=DummyDB(),
                copilot=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "content is required"


def test_weekly_feedback_endpoint_invalid_json_soft_fallback(monkeypatch):
    target_week = date(2026, 2, 16)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()
    snippet = WeeklySnippetStub(target_week, content="raw weekly content")
    db = DummyDB()

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_user_and_week(db, user_id, week):
        return snippet

    async def fake_generate_feedback_with_ai(
        daily_snippet_content,
        organized_content,
        playbook_content,
        copilot,
        prompt_name="daily_feedback.md",
        snippet_label="Daily Snippet",
    ):
        return "not-a-json"

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: target_week)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_user_and_week", fake_get_weekly_snippet_by_user_and_week)
    monkeypatch.setattr(_snippet_utils, "generate_feedback_with_ai", fake_generate_feedback_with_ai)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.generate_weekly_snippet_feedback)(
            request=_make_request(),
            db=db,
            copilot=object(),
        )
    )

    assert result.week == target_week
    assert result.feedback is None
    assert snippet.feedback is None
    assert db.committed is True
