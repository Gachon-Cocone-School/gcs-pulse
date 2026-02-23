import asyncio
from datetime import date, datetime, timezone
import inspect
import json

from starlette.requests import Request

from app import crud
from app.routers import snippet_utils as _snippet_utils
from app.routers import weekly_snippets


class DummyDB:
    async def refresh(self, _snippet):
        return None


class WeeklySnippetStub:
    def __init__(self, week: date):
        self.id = 1
        self.user_id = 1
        self.week = week
        self.content = "weekly raw"
        self.structured = None
        self.playbook = "existing weekly playbook"
        self.feedback = None


def _make_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/weekly-snippets/organize",
        "headers": [],
    }
    return Request(scope)


def test_weekly_organize_uses_weekly_prompts(monkeypatch):
    target_week = date(2026, 2, 16)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()
    snippet = WeeklySnippetStub(target_week)
    db = DummyDB()

    captured: dict[str, str] = {}

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_user_and_week(db, user_id, week):
        return snippet

    async def fake_organize_content_with_ai(content, copilot, prompt_name="organize_daily.md"):
        captured["organize_prompt_name"] = prompt_name
        return "#### weekly structured\n- done"

    async def fake_generate_feedback_with_ai(
        daily_snippet_content,
        organized_content,
        playbook_content,
        copilot,
        prompt_name="daily_feedback.md",
        snippet_label="Daily Snippet",
    ):
        captured["feedback_prompt_name"] = prompt_name
        captured["snippet_label"] = snippet_label
        return json.dumps(
            {
                "total_score": 88,
                "scores": {"record_completeness": {"score": 12, "max_score": 15}},
                "playbook_update_markdown": "## weekly update",
            }
        )

    async def fake_update_weekly_snippet(
        db,
        snippet,
        content,
        structured=None,
        playbook=None,
        feedback=None,
    ):
        snippet.content = content
        if structured is not None:
            snippet.structured = structured
        if playbook is not None:
            snippet.playbook = playbook
        if feedback is not None:
            snippet.feedback = feedback
        return snippet

    monkeypatch.setattr(_snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(_snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: target_week)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_user_and_week", fake_get_weekly_snippet_by_user_and_week)
    monkeypatch.setattr(_snippet_utils, "organize_content_with_ai", fake_organize_content_with_ai)
    monkeypatch.setattr(_snippet_utils, "generate_feedback_with_ai", fake_generate_feedback_with_ai)
    monkeypatch.setattr(crud, "update_weekly_snippet", fake_update_weekly_snippet)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.organize_weekly_snippet)(
            request=_make_request(),
            db=db,
            copilot=object(),
        )
    )

    assert captured["organize_prompt_name"] == "organize_weekly.md"
    assert captured["feedback_prompt_name"] == "weekly_feedback.md"
    assert captured["snippet_label"] == "Weekly Snippet"
    assert result.structured == "#### weekly structured\n- done"
    assert result.feedback is not None
