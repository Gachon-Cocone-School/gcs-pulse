import asyncio
from datetime import date, datetime, timezone
import inspect

from starlette.requests import Request

from app import crud
from app.routers import daily_snippets
from app.routers import snippet_utils
from app.schemas import DailySnippetOrganizeRequest


class DummyDB:
    async def refresh(self, _snippet):
        return None


class DailySnippetStub:
    def __init__(self, target_date: date):
        self.id = 3
        self.user_id = 1
        self.date = target_date
        self.content = "daily raw"
        self.playbook = "existing daily playbook"
        self.feedback = None


def _make_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/daily-snippets/organize",
        "headers": [],
    }
    return Request(scope)


def test_daily_organize_keeps_default_prompts(monkeypatch):
    target_date = date(2026, 2, 23)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()
    snippet = DailySnippetStub(target_date)
    db = DummyDB()

    captured: dict[str, str] = {}

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_daily_snippet_by_user_and_date(db, user_id, snippet_date):
        return snippet

    async def fake_organize_content_with_ai(content, copilot, prompt_name="organize_daily.md"):
        captured["organize_prompt_name"] = prompt_name
        return "#### daily structured\n- done"

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: target_date)
    monkeypatch.setattr(crud, "get_daily_snippet_by_user_and_date", fake_get_daily_snippet_by_user_and_date)
    monkeypatch.setattr(snippet_utils, "organize_content_with_ai", fake_organize_content_with_ai)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.organize_daily_snippet)(
            payload=DailySnippetOrganizeRequest(content=snippet.content),
            request=_make_request(),
            db=db,
            copilot=object(),
        )
    )

    assert captured["organize_prompt_name"] == "organize_daily.md"
    assert result.organized_content == "#### daily structured\n- done"
