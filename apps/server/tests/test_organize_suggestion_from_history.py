import asyncio
from datetime import date, datetime, timedelta, timezone
import inspect

from starlette.requests import Request

from app import crud
from app.routers import daily_snippets
from app.routers import snippet_utils
from app.routers import weekly_snippets


class DummyDB:
    async def refresh(self, _snippet):
        return None


class DailySnippetStub:
    def __init__(self, snippet_id: int, user_id: int, target_date: date, content: str):
        self.id = snippet_id
        self.user_id = user_id
        self.date = target_date
        self.content = content
        self.structured = None
        self.playbook = "existing daily playbook"
        self.feedback = None


class WeeklySnippetStub:
    def __init__(self, snippet_id: int, user_id: int, week: date, content: str):
        self.id = snippet_id
        self.user_id = user_id
        self.week = week
        self.content = content
        self.structured = None
        self.playbook = "existing weekly playbook"
        self.feedback = None


class DailyContextItem:
    def __init__(self, target_date: date, content: str, structured: str | None = None):
        self.date = target_date
        self.content = content
        self.structured = structured


def _make_daily_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/daily-snippets/organize",
            "headers": [],
        }
    )


def _make_weekly_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/weekly-snippets/organize",
            "headers": [],
        }
    )


def test_daily_organize_empty_content_generates_suggestion_from_previous_day(monkeypatch):
    target_date = date(2026, 2, 23)
    previous_date = target_date - timedelta(days=1)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()
    db = DummyDB()

    current_snippet = DailySnippetStub(snippet_id=10, user_id=1, target_date=target_date, content="")
    previous_snippet = DailyContextItem(
        target_date=previous_date,
        content="yesterday raw content",
        structured="#### yesterday structured\n- key point",
    )

    captured: dict[str, object] = {}

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_daily_snippet_by_user_and_date(db, user_id, snippet_date):
        if snippet_date == target_date:
            return None
        if snippet_date == previous_date:
            return previous_snippet
        return None

    async def fake_upsert_daily_snippet(db, user_id, snippet_date, content, structured=None, playbook=None, feedback=None):
        captured["upsert_content"] = content
        return current_snippet

    async def fake_organize_content_with_ai(content, copilot, prompt_name="organize_daily.md"):
        captured["prompt_name"] = prompt_name
        captured["suggestion_source"] = content
        return "#### suggested daily\n- from previous"

    async def fake_generate_feedback_with_ai(*args, **kwargs):
        raise AssertionError("Feedback generation should be skipped for empty-content suggestion flow")

    async def fake_update_daily_snippet(db, snippet, content, structured=None, playbook=None, feedback=None):
        captured["updated_feedback"] = feedback
        snippet.content = content
        if structured is not None:
            snippet.structured = structured
        if playbook is not None:
            snippet.playbook = playbook
        if feedback is not None:
            snippet.feedback = feedback
        return snippet

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: target_date)
    monkeypatch.setattr(crud, "get_daily_snippet_by_user_and_date", fake_get_daily_snippet_by_user_and_date)
    monkeypatch.setattr(crud, "upsert_daily_snippet", fake_upsert_daily_snippet)
    monkeypatch.setattr(snippet_utils, "organize_content_with_ai", fake_organize_content_with_ai)
    monkeypatch.setattr(snippet_utils, "generate_feedback_with_ai", fake_generate_feedback_with_ai)
    monkeypatch.setattr(crud, "update_daily_snippet", fake_update_daily_snippet)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.organize_daily_snippet)(
            request=_make_daily_request(),
            db=db,
            copilot=object(),
        )
    )

    assert captured["upsert_content"] == ""
    assert captured["prompt_name"] == "suggest_daily_from_previous.md"
    assert "전날 스니펫" in str(captured["suggestion_source"])
    assert "#### yesterday structured" in str(captured["suggestion_source"])
    assert captured["updated_feedback"] == ""
    assert result.structured == "#### suggested daily\n- from previous"
    assert result.feedback == ""


def test_weekly_organize_empty_content_generates_suggestion_from_weekly_dailies(monkeypatch):
    target_week = date(2026, 2, 23)
    request_now = datetime(2026, 2, 23, 12, 0, tzinfo=timezone.utc)

    viewer = type("Viewer", (), {"id": 1})()
    db = DummyDB()

    current_weekly = WeeklySnippetStub(snippet_id=20, user_id=1, week=target_week, content="")
    daily_item_1 = DailyContextItem(
        target_date=date(2026, 2, 23),
        content="day1 raw",
        structured="#### day1 structured\n- milestone",
    )
    daily_item_2 = DailyContextItem(
        target_date=date(2026, 2, 25),
        content="day3 raw",
        structured=None,
    )

    captured: dict[str, object] = {}

    async def fake_get_viewer_or_401(request, db):
        return viewer

    async def fake_get_weekly_snippet_by_user_and_week(db, user_id, week):
        return None

    async def fake_upsert_weekly_snippet(db, user_id, week, content, structured=None, playbook=None, feedback=None):
        captured["upsert_content"] = content
        return current_weekly

    async def fake_list_daily_snippets(db, viewer, limit, offset, order, from_date, to_date, q, scope):
        captured["list_from_date"] = from_date
        captured["list_to_date"] = to_date
        captured["list_limit"] = limit
        captured["list_order"] = order
        return [daily_item_1, daily_item_2], 2

    async def fake_organize_content_with_ai(content, copilot, prompt_name="organize_daily.md"):
        captured["prompt_name"] = prompt_name
        captured["suggestion_source"] = content
        return "#### suggested weekly\n- from week history"

    async def fake_generate_feedback_with_ai(*args, **kwargs):
        raise AssertionError("Feedback generation should be skipped for empty-content suggestion flow")

    async def fake_update_weekly_snippet(db, snippet, content, structured=None, playbook=None, feedback=None):
        captured["updated_feedback"] = feedback
        snippet.content = content
        if structured is not None:
            snippet.structured = structured
        if playbook is not None:
            snippet.playbook = playbook
        if feedback is not None:
            snippet.feedback = feedback
        return snippet

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda request: request_now)
    monkeypatch.setattr(weekly_snippets, "current_business_key", lambda kind, now: target_week)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_user_and_week", fake_get_weekly_snippet_by_user_and_week)
    monkeypatch.setattr(crud, "upsert_weekly_snippet", fake_upsert_weekly_snippet)
    monkeypatch.setattr(crud, "list_daily_snippets", fake_list_daily_snippets)
    monkeypatch.setattr(snippet_utils, "organize_content_with_ai", fake_organize_content_with_ai)
    monkeypatch.setattr(snippet_utils, "generate_feedback_with_ai", fake_generate_feedback_with_ai)
    monkeypatch.setattr(crud, "update_weekly_snippet", fake_update_weekly_snippet)

    result = asyncio.run(
        inspect.unwrap(weekly_snippets.organize_weekly_snippet)(
            request=_make_weekly_request(),
            db=db,
            copilot=object(),
        )
    )

    assert captured["upsert_content"] == ""
    assert captured["list_from_date"] == target_week
    assert captured["list_to_date"] == target_week + timedelta(days=6)
    assert captured["list_limit"] == 7
    assert captured["list_order"] == "asc"
    assert captured["prompt_name"] == "organize_weekly.md"
    assert "이번 주 Daily Snippets" in str(captured["suggestion_source"])
    assert "### 2026-02-23" in str(captured["suggestion_source"])
    assert "day3 raw" in str(captured["suggestion_source"])
    assert captured["updated_feedback"] == ""
    assert result.structured == "#### suggested weekly\n- from week history"
    assert result.feedback == ""
