import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast

from starlette.requests import Request

from app.routers import mentoring_chat
from app.services.mentoring_agent_service import MentoringAgentResult


class _DummyRequest:
    async def is_disconnected(self) -> bool:
        return False


class _DummyDB:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1

    async def refresh(self, _obj):
        return None


def test_stream_single_reply_emits_delta_and_done(monkeypatch):
    db = _DummyDB()
    session = SimpleNamespace(id=11)
    memory = SimpleNamespace(memory_markdown="- 기존")
    created_messages = []
    created_actions = []

    async def fake_get_session_by_id_and_professor(db, session_id, professor_user_id):
        _ = (db, session_id, professor_user_id)
        return session

    async def fake_create_message(
        db,
        *,
        session_id,
        role,
        content_markdown,
        tokens_input=None,
        tokens_output=None,
        latency_ms=None,
        tool_calls_json=None,
    ):
        row = SimpleNamespace(
            id=len(created_messages) + 1,
            session_id=session_id,
            role=role,
            content_markdown=content_markdown,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            tool_calls_json=tool_calls_json,
        )
        created_messages.append(row)
        return row

    async def fake_create_action_log(db, **kwargs):
        _ = db
        created_actions.append(kwargs)
        return SimpleNamespace(id=91, **kwargs)

    async def fake_get_or_create_professor_memory(db, professor_user_id):
        _ = (db, professor_user_id)
        return memory

    async def fake_update_professor_memory(db, **kwargs):
        _ = (db, kwargs)
        return None

    class _FakeAgent:
        async def generate_reply_streaming(self, *, user_message, memory_markdown, on_delta):
            _ = (user_message, memory_markdown)
            await on_delta("안")
            await on_delta("녕")
            return MentoringAgentResult(
                content_markdown="안녕",
                tool_calls=[],
                latency_ms=123,
                tokens_input=10,
                tokens_output=20,
            )

        async def summarize_memory(self, **kwargs):
            _ = kwargs
            return "- 갱신"

    monkeypatch.setattr(mentoring_chat.crud_mentoring, "get_session_by_id_and_professor", fake_get_session_by_id_and_professor)
    monkeypatch.setattr(mentoring_chat.crud_mentoring, "create_message", fake_create_message)
    monkeypatch.setattr(mentoring_chat.crud_mentoring, "create_action_log", fake_create_action_log)
    monkeypatch.setattr(mentoring_chat, "get_or_create_professor_memory", fake_get_or_create_professor_memory)
    monkeypatch.setattr(mentoring_chat, "update_professor_memory", fake_update_professor_memory)
    monkeypatch.setattr(mentoring_chat, "MentoringAgentService", _FakeAgent)

    async def _run():
        events = []
        async for event in mentoring_chat._stream_single_reply(
            cast(Request, _DummyRequest()),
            db=db,
            professor_id=7,
            session_id=11,
            content="질문",
        ):
            events.append(event)
        return events

    events = asyncio.run(_run())

    assert [event["event"] for event in events] == [
        "mentoring_chat_delta",
        "mentoring_chat_delta",
        "mentoring_chat_done",
    ]
    assert json.loads(events[0]["data"])["delta"] == "안"
    assert json.loads(events[1]["data"])["delta"] == "녕"
    done_payload = json.loads(events[2]["data"])
    assert done_payload["role"] == "assistant"

    assert len(created_messages) == 2
    assert created_messages[0].role == "user"
    assert created_messages[1].role == "assistant"
    assert created_messages[1].tokens_input == 10
    assert created_messages[1].tokens_output == 20
    assert created_actions[0]["status"] == "proposed"


def test_stream_single_reply_emits_error_event_on_agent_failure(monkeypatch):
    db = _DummyDB()
    session = SimpleNamespace(id=11)

    async def fake_get_session_by_id_and_professor(db, session_id, professor_user_id):
        _ = (db, session_id, professor_user_id)
        return session

    async def fake_create_message(db, **kwargs):
        _ = (db, kwargs)
        return SimpleNamespace(id=1, session_id=11, role="user")

    async def fake_get_or_create_professor_memory(db, professor_user_id):
        _ = (db, professor_user_id)
        return SimpleNamespace(memory_markdown="")

    class _FakeAgent:
        async def generate_reply_streaming(self, *, user_message, memory_markdown, on_delta):
            _ = (user_message, memory_markdown, on_delta)
            raise RuntimeError("agent failed")

        async def summarize_memory(self, **kwargs):
            _ = kwargs
            return ""

    monkeypatch.setattr(mentoring_chat.crud_mentoring, "get_session_by_id_and_professor", fake_get_session_by_id_and_professor)
    monkeypatch.setattr(mentoring_chat.crud_mentoring, "create_message", fake_create_message)
    monkeypatch.setattr(mentoring_chat, "get_or_create_professor_memory", fake_get_or_create_professor_memory)
    monkeypatch.setattr(mentoring_chat, "MentoringAgentService", _FakeAgent)

    async def _run():
        events = []
        async for event in mentoring_chat._stream_single_reply(
            cast(Request, _DummyRequest()),
            db=db,
            professor_id=7,
            session_id=11,
            content="질문",
        ):
            events.append(event)
        return events

    events = asyncio.run(_run())
    assert [event["event"] for event in events] == ["error"]
    assert "agent failed" in json.loads(events[0]["data"])["detail"]


def test_approve_action_keeps_state_machine_transition(monkeypatch):
    db = _DummyDB()
    professor = SimpleNamespace(id=7)
    action = SimpleNamespace(
        id=1,
        session_id=2,
        message_id=3,
        action_type="post_comment",
        status="proposed",
        action_payload_json={"content": "좋은 시도", "daily_snippet_id": 10},
        approved_by_user_id=None,
        executed_at=None,
        error_message=None,
        created_at=datetime.now(timezone.utc),
    )

    async def fake_get_professor_or_403(request, db):
        _ = (request, db)
        return professor

    async def fake_get_action_by_id(db, action_id):
        _ = (db, action_id)
        return action

    async def fake_get_session_by_id_and_professor(db, session_id, professor_user_id):
        _ = (db, session_id, professor_user_id)
        return SimpleNamespace(id=session_id)

    async def fake_execute_comment_action_or_400(db, *, professor, payload):
        _ = (db, professor, payload)
        return {"executed_comment_id": 99}

    monkeypatch.setattr(mentoring_chat, "_get_professor_or_403", fake_get_professor_or_403)
    monkeypatch.setattr(mentoring_chat.crud_mentoring, "get_action_by_id", fake_get_action_by_id)
    monkeypatch.setattr(mentoring_chat.crud_mentoring, "get_session_by_id_and_professor", fake_get_session_by_id_and_professor)
    monkeypatch.setattr(mentoring_chat, "_execute_comment_action_or_400", fake_execute_comment_action_or_400)

    response = asyncio.run(mentoring_chat.approve_action(action_id=1, request=SimpleNamespace(), db=db))

    assert action.status == "executed"
    assert response.action.status == "executed"
    assert response.action.approved_by_user_id == 7
    assert response.action.action_payload_json["execution_result"]["executed_comment_id"] == 99


def test_reject_action_keeps_state_machine_transition(monkeypatch):
    db = _DummyDB()
    professor = SimpleNamespace(id=7)
    action = SimpleNamespace(
        id=2,
        session_id=2,
        message_id=3,
        action_type="suggest_comment",
        status="proposed",
        action_payload_json={"source_message_id": 3},
        approved_by_user_id=None,
        executed_at=None,
        error_message=None,
        created_at=datetime.now(timezone.utc),
    )

    async def fake_get_professor_or_403(request, db):
        _ = (request, db)
        return professor

    async def fake_get_action_by_id(db, action_id):
        _ = (db, action_id)
        return action

    async def fake_get_session_by_id_and_professor(db, session_id, professor_user_id):
        _ = (db, session_id, professor_user_id)
        return SimpleNamespace(id=session_id)

    monkeypatch.setattr(mentoring_chat, "_get_professor_or_403", fake_get_professor_or_403)
    monkeypatch.setattr(mentoring_chat.crud_mentoring, "get_action_by_id", fake_get_action_by_id)
    monkeypatch.setattr(mentoring_chat.crud_mentoring, "get_session_by_id_and_professor", fake_get_session_by_id_and_professor)

    response = asyncio.run(mentoring_chat.reject_action(action_id=2, request=SimpleNamespace(), db=db))

    assert action.status == "rejected"
    assert response.action.status == "rejected"
    assert response.action.approved_by_user_id == 7
