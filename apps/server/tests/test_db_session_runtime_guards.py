import asyncio
import inspect
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any

from starlette.requests import Request

from app import crud
from app.routers import auth, daily_snippets, mcp, peer_reviews, tournaments
from app.routers import snippet_utils


class _FakeDB:
    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, _obj):
        return None


class _SessionTracker:
    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.enter_count = 0

    def __call__(self):
        tracker = self

        class _TrackedSession:
            async def __aenter__(self):
                tracker.active += 1
                tracker.enter_count += 1
                tracker.max_active = max(tracker.max_active, tracker.active)
                return _FakeDB()

            async def __aexit__(self, exc_type, exc, tb):
                tracker.active -= 1
                return False

        return _TrackedSession()


def _make_request(path: str = "/", method: str = "GET", email: str = "prof@example.com") -> Request:
    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "session": {"user": {"email": email}},
        },
        receive=receive,
    )


def test_oauth_token_exchange_runs_without_active_db_session(monkeypatch):
    tracker = _SessionTracker()
    request = _make_request("/auth/google/callback")

    monkeypatch.setattr(auth, "AsyncSessionLocal", tracker)
    monkeypatch.setattr(auth.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(auth.settings, "TEST_AUTH_BYPASS_ENABLED", False)

    class FakeClient:
        async def authorize_access_token(self, _request):
            assert tracker.active == 0
            return {
                "userinfo": {
                    "email": "prof@example.com",
                    "name": "Professor",
                    "picture": "",
                    "email_verified": True,
                }
            }

    async def fake_create_or_update_user(db, user_info):
        assert tracker.active == 1
        return SimpleNamespace(id=1, **user_info)

    async def fake_clear_provisional_flag(db, user):
        assert tracker.active == 1
        return user

    monkeypatch.setattr(auth.oauth, "create_client", lambda name: FakeClient())
    monkeypatch.setattr(crud, "create_or_update_user", fake_create_or_update_user)
    monkeypatch.setattr(crud, "clear_provisional_flag", fake_clear_provisional_flag)

    response = asyncio.run(auth.auth_callback(request))

    assert response.status_code in (302, 307)
    assert tracker.enter_count == 1
    assert tracker.active == 0


def test_peer_review_parse_copilot_runs_without_active_db_session(monkeypatch):
    tracker = _SessionTracker()

    monkeypatch.setattr(peer_reviews, "AsyncSessionLocal", tracker)

    async def fake_get_professor_or_403(request, db):
        assert tracker.active == 1
        return SimpleNamespace(id=7)

    async def fake_list_student_users(db):
        assert tracker.active == 1
        return []

    async def fake_parse_team_text_with_copilot(*, raw_text, copilot):
        assert tracker.active == 0
        return []

    monkeypatch.setattr(peer_reviews, "_get_professor_or_403", fake_get_professor_or_403)
    monkeypatch.setattr(peer_reviews, "_list_student_users", fake_list_student_users)
    monkeypatch.setattr(peer_reviews, "_parse_team_text_with_copilot", fake_parse_team_text_with_copilot)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.parse_peer_review_members_draft)(
            payload=SimpleNamespace(raw_text="1조: 홍길동"),
            request=_make_request("/peer-reviews/members:parse", method="POST"),
            copilot=object(),
        )
    )

    assert result.teams == {}
    assert result.unresolved_members == []
    assert tracker.active == 0


def test_tournament_format_parse_copilot_runs_between_short_db_sessions(monkeypatch):
    tracker = _SessionTracker()
    session = SimpleNamespace(id=55, format_text=None, format_json=None)

    monkeypatch.setattr(tournaments, "AsyncSessionLocal", tracker)

    async def fake_get_professor_or_403(request, db):
        assert tracker.active == 1
        return SimpleNamespace(id=7)

    async def fake_get_professor_session_or_404(db, *, session_id, professor_user_id):
        assert tracker.active == 1
        assert session_id == 55
        assert professor_user_id == 7
        return session

    async def fake_parse_format_text_with_copilot(*, format_text, copilot):
        assert tracker.active == 0
        return {"bracket_size": 4, "repechage": {"enabled": False}}

    async def fake_update_session_format(db, *, session, format_text, format_json):
        assert tracker.active == 1
        session.format_text = format_text
        session.format_json = format_json
        return session

    monkeypatch.setattr(tournaments, "_get_professor_or_403", fake_get_professor_or_403)
    monkeypatch.setattr(tournaments, "_get_professor_session_or_404", fake_get_professor_session_or_404)
    monkeypatch.setattr(tournaments, "_parse_format_text_with_copilot", fake_parse_format_text_with_copilot)
    monkeypatch.setattr(tournaments.tournament_crud, "update_session_format", fake_update_session_format)

    result = asyncio.run(
        inspect.unwrap(tournaments.parse_tournament_format)(
            session_id=55,
            payload=SimpleNamespace(format_text="4 team single elimination"),
            request=_make_request("/tournaments/sessions/55/format:parse", method="POST"),
            copilot=object(),
        )
    )

    assert result.format_json == {"bracket_size": 4, "repechage": {"enabled": False}}
    assert tracker.enter_count == 2
    assert tracker.active == 0


def test_daily_feedback_ai_runs_without_active_db_and_persists_refetched_snippet(monkeypatch):
    tracker = _SessionTracker()
    target_date = date(2026, 2, 23)
    original_snippet = SimpleNamespace(
        id=10,
        user_id=1,
        date=target_date,
        content="daily content",
        playbook="daily playbook",
        feedback=None,
    )
    refetched_snippet = SimpleNamespace(id=10, feedback=None)

    monkeypatch.setattr(daily_snippets, "AsyncSessionLocal", tracker)
    monkeypatch.setattr(snippet_utils, "get_request_now", lambda request: datetime(2026, 2, 23, tzinfo=timezone.utc))
    monkeypatch.setattr(daily_snippets, "current_business_key", lambda kind, now: target_date)

    async def fake_get_viewer_or_401(request, db):
        assert tracker.active == 1
        return SimpleNamespace(id=1)

    async def fake_get_daily_snippet_by_user_and_date(db, user_id, snippet_date):
        assert tracker.active == 1
        return original_snippet

    async def fake_generate_feedback_json_or_none(**kwargs):
        assert tracker.active == 0
        return "feedback-json"

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        assert tracker.active == 1
        assert snippet_id == original_snippet.id
        return refetched_snippet

    async def fake_persist_snippet_feedback(db, snippet, feedback_json):
        assert tracker.active == 1
        assert snippet is refetched_snippet
        snippet.feedback = feedback_json

    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(crud, "get_daily_snippet_by_user_and_date", fake_get_daily_snippet_by_user_and_date)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(daily_snippets._flow, "generate_feedback_json_or_none", fake_generate_feedback_json_or_none)
    monkeypatch.setattr(daily_snippets._flow, "persist_snippet_feedback", fake_persist_snippet_feedback)

    result = asyncio.run(
        inspect.unwrap(daily_snippets.generate_daily_snippet_feedback)(
            request=_make_request("/daily-snippets/feedback"),
            copilot=object(),
        )
    )

    assert result.feedback == "feedback-json"
    assert refetched_snippet.feedback == "feedback-json"
    assert tracker.active == 0


def test_mcp_daily_feedback_ai_runs_without_active_db_and_persists_refetched_snippet(monkeypatch):
    tracker = _SessionTracker()
    target_date = date(2026, 2, 23)
    original_snippet = SimpleNamespace(id=33, content="daily content", playbook="daily playbook")
    refetched_snippet = SimpleNamespace(id=33, feedback=None)

    monkeypatch.setattr(mcp, "AsyncSessionLocal", tracker)
    monkeypatch.setattr(mcp, "_ctx_request", lambda: _make_request("/mcp"))

    async def fake_get_copilot_client(request):
        assert tracker.active == 0
        return object()

    async def fake_get_snippet_feedback_context(**kwargs):
        assert tracker.active == 1
        return target_date, original_snippet

    async def fake_generate_feedback_json_or_none(**kwargs):
        assert tracker.active == 0
        return "feedback-json"

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        assert tracker.active == 1
        assert snippet_id == original_snippet.id
        return refetched_snippet

    async def fake_persist_snippet_feedback(db, snippet, feedback_json):
        assert tracker.active == 1
        assert snippet is refetched_snippet
        snippet.feedback = feedback_json

    monkeypatch.setattr(mcp, "get_copilot_client", fake_get_copilot_client)
    monkeypatch.setattr(mcp._flow, "get_snippet_feedback_context", fake_get_snippet_feedback_context)
    monkeypatch.setattr(mcp._flow, "generate_feedback_json_or_none", fake_generate_feedback_json_or_none)
    monkeypatch.setattr(mcp.crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(mcp._flow, "persist_snippet_feedback", fake_persist_snippet_feedback)

    result = asyncio.run(mcp._run_daily_feedback({}))

    assert result == {"date": target_date.isoformat(), "feedback": "feedback-json"}
    assert refetched_snippet.feedback == "feedback-json"
    assert tracker.active == 0


def test_mcp_daily_organize_uses_fresh_session_for_suggestion_source_and_no_db_for_ai(monkeypatch):
    tracker = _SessionTracker()
    target_date = date(2026, 2, 23)
    current_snippet = SimpleNamespace(id=44, playbook="daily playbook")
    previous_snippet = SimpleNamespace(id=43, content="previous content")

    monkeypatch.setattr(mcp, "AsyncSessionLocal", tracker)
    monkeypatch.setattr(mcp, "_ctx_request", lambda: _make_request("/mcp"))
    monkeypatch.setattr(mcp, "_ctx_user", lambda: SimpleNamespace(id=1, roles=["gcs"]))
    monkeypatch.setattr(mcp._snippet_utils, "get_request_now", lambda request: datetime(2026, 2, 23, tzinfo=timezone.utc))
    monkeypatch.setattr(mcp, "current_business_key", lambda kind, now: target_date)

    async def fake_get_copilot_client(request):
        assert tracker.active == 0
        return object()

    async def fake_get_daily_snippet_by_user_and_date(db, user_id, snippet_date):
        assert tracker.active == 1
        if snippet_date == target_date:
            return current_snippet
        assert snippet_date == target_date.replace(day=22)
        return previous_snippet

    async def fake_organize_content_with_ai(content, copilot, prompt_name="organize_daily.md", **kwargs):
        assert tracker.active == 0
        assert "previous content" in content
        return "organized content"

    async def fake_generate_feedback_json_or_none(**kwargs):
        assert tracker.active == 0
        return "feedback-json"

    monkeypatch.setattr(mcp, "get_copilot_client", fake_get_copilot_client)
    monkeypatch.setattr(mcp.crud, "get_daily_snippet_by_user_and_date", fake_get_daily_snippet_by_user_and_date)
    monkeypatch.setattr(mcp._snippet_utils, "organize_content_with_ai", fake_organize_content_with_ai)
    monkeypatch.setattr(mcp._flow, "generate_feedback_json_or_none", fake_generate_feedback_json_or_none)

    result = asyncio.run(mcp._run_daily_organize({"content": ""}))

    assert result["date"] == target_date.isoformat()
    assert result["organized_content"] == "organized content"
    assert result["feedback"] == "feedback-json"
    assert tracker.enter_count == 2
    assert tracker.active == 0


def test_peer_review_status_notification_runs_without_active_db_session(monkeypatch):
    tracker = _SessionTracker()
    now = datetime(2026, 2, 23, tzinfo=timezone.utc)
    session = SimpleNamespace(
        id=9,
        title="Review",
        professor_user_id=7,
        is_open=False,
        access_token="token",
        created_at=now,
        updated_at=now,
    )
    member = SimpleNamespace(student_user_id=101, team_label="A")
    student = SimpleNamespace(id=101, name="Student", email="student@example.com")

    monkeypatch.setattr(peer_reviews, "AsyncSessionLocal", tracker)

    async def fake_get_professor_or_403(request, db):
        assert tracker.active == 1
        return SimpleNamespace(id=7)

    async def fake_get_professor_session_or_404(db, *, session_id, professor_user_id):
        assert tracker.active == 1
        return session

    async def fake_update_session_is_open(db, *, session, is_open):
        assert tracker.active == 1
        session.is_open = is_open
        return session

    async def fake_list_session_members(db, session_id):
        assert tracker.active == 1
        return [(member, student)]

    async def fake_send_to_user(user_id, payload):
        assert tracker.active == 0
        assert user_id == 101
        assert payload["event"] == "peer_review_session_status"

    monkeypatch.setattr(peer_reviews, "_get_professor_or_403", fake_get_professor_or_403)
    monkeypatch.setattr(peer_reviews, "_get_professor_session_or_404", fake_get_professor_session_or_404)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "update_session_is_open", fake_update_session_is_open)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_session_members", fake_list_session_members)
    monkeypatch.setattr(peer_reviews.notification_registry, "send_to_user", fake_send_to_user)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.update_peer_review_session_status)(
            session_id=9,
            payload=SimpleNamespace(is_open=True),
            request=_make_request("/peer-reviews/sessions/9/status", method="PATCH"),
        )
    )

    assert result.is_open is True
    assert tracker.active == 0
