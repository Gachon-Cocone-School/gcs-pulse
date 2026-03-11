import asyncio
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.routers import peer_reviews as _peer_reviews

peer_reviews = cast(Any, _peer_reviews)


def _make_request(path: str, method: str = "POST") -> Request:
    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "session": {"user": {"email": "prof@example.com"}},
        },
        receive=receive,
    )


def test_create_peer_review_session_success(monkeypatch):
    request = _make_request("/peer-reviews/sessions")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "prof@example.com"
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_create_session(_db, **kwargs):
        assert kwargs["title"] == "중간고사"
        assert kwargs["professor_user_id"] == 7
        assert kwargs["access_token"]
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=11,
            title=kwargs["title"],
            professor_user_id=kwargs["professor_user_id"],
            is_open=True,
            access_token=kwargs["access_token"],
            raw_text=None,
            created_at=now,
            updated_at=now,
        )

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "create_session", fake_create_session)

    payload = SimpleNamespace(title="중간고사")

    result = asyncio.run(
        inspect.unwrap(peer_reviews.create_peer_review_session)(
            payload=payload,
            request=request,
            db=object(),
        )
    )

    assert result.id == 11
    assert result.raw_text is None
    assert result.form_url.endswith(f"/peer-reviews/forms/{result.access_token}")


def test_list_peer_review_sessions_success(monkeypatch):
    request = _make_request("/peer-reviews/sessions", method="GET")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    now = datetime.now(timezone.utc)

    async def fake_list_sessions_by_professor(_db, *, professor_user_id):
        assert professor_user_id == 7
        return [
            (
                SimpleNamespace(
                    id=11,
                    title="중간고사",
                    is_open=True,
                    created_at=now,
                    updated_at=now,
                ),
                3,
                2,
            )
        ]

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_sessions_by_professor", fake_list_sessions_by_professor)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.list_peer_review_sessions)(
            request=request,
            db=object(),
        )
    )

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].id == 11
    assert result.items[0].member_count == 3
    assert result.items[0].submitted_evaluators == 2


def test_list_peer_review_sessions_returns_empty_list(monkeypatch):
    request = _make_request("/peer-reviews/sessions", method="GET")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_list_sessions_by_professor(_db, *, professor_user_id):
        assert professor_user_id == 7
        return []

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_sessions_by_professor", fake_list_sessions_by_professor)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.list_peer_review_sessions)(
            request=request,
            db=object(),
        )
    )

    assert result.total == 0
    assert result.items == []


def test_list_peer_review_sessions_requires_professor(monkeypatch):
    request = _make_request("/peer-reviews/sessions", method="GET")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["가천대학교"], email=email)

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.list_peer_review_sessions)(
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_list_peer_review_sessions_preserves_latest_order(monkeypatch):
    request = _make_request("/peer-reviews/sessions", method="GET")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    now = datetime.now(timezone.utc)

    async def fake_list_sessions_by_professor(_db, *, professor_user_id):
        assert professor_user_id == 7
        return [
            (
                SimpleNamespace(
                    id=12,
                    title="최신 세션",
                    is_open=True,
                    created_at=now,
                    updated_at=now,
                ),
                4,
                3,
            ),
            (
                SimpleNamespace(
                    id=11,
                    title="이전 세션",
                    is_open=False,
                    created_at=now,
                    updated_at=now,
                ),
                2,
                1,
            ),
        ]

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_sessions_by_professor", fake_list_sessions_by_professor)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.list_peer_review_sessions)(
            request=request,
            db=object(),
        )
    )

    assert [item.id for item in result.items] == [12, 11]


def test_confirm_members_rejects_duplicate_student(monkeypatch):
    request = _make_request("/peer-reviews/sessions/1/members:confirm")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return SimpleNamespace(id=1, professor_user_id=7)

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)

    payload = SimpleNamespace(
        members=[
            SimpleNamespace(student_user_id=101, team_label="1조"),
            SimpleNamespace(student_user_id=101, team_label="1조"),
        ],
        unresolved_members=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.confirm_peer_review_members)(
                session_id=1,
                payload=payload,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Duplicate student in members"


def test_update_peer_review_session_success(monkeypatch):
    request = _make_request("/peer-reviews/sessions/33", method="PATCH")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return SimpleNamespace(
            id=33,
            title="기존 제목",
            professor_user_id=7,
            is_open=True,
            access_token="token-33",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def fake_update_session(_db, *, session, title):
        session.title = title
        return session

    async def fake_list_session_members(_db, *, session_id):
        assert session_id == 33
        return [
            (
                SimpleNamespace(session_id=33, student_user_id=1001, team_label="1조"),
                SimpleNamespace(id=1001, name="학생A", email="a@example.com"),
            )
        ]

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "update_session", fake_update_session)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_session_members", fake_list_session_members)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.update_peer_review_session)(
            session_id=33,
            payload=SimpleNamespace(title="수정된 제목"),
            request=request,
            db=object(),
        )
    )

    assert result.id == 33
    assert result.title == "수정된 제목"
    assert result.raw_text == "1조: 학생A"
    assert len(result.members) == 1


def test_get_confirm_update_session_flow_success(monkeypatch):
    get_request = _make_request("/peer-reviews/sessions/44", method="GET")
    confirm_request = _make_request("/peer-reviews/sessions/44/members:confirm")
    update_request = _make_request("/peer-reviews/sessions/44", method="PATCH")

    session_obj = SimpleNamespace(
        id=44,
        title="초기 제목",
        professor_user_id=7,
        is_open=True,
        access_token="token-44",
        raw_text="1조: 학생A, 학생B",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    member_state = {
        "items": [
            SimpleNamespace(session_id=44, student_user_id=2001, team_label="1조"),
            SimpleNamespace(session_id=44, student_user_id=2002, team_label="1조"),
        ]
    }

    users_by_id = {
        2001: SimpleNamespace(id=2001, name="학생A", email="a@example.com"),
        2002: SimpleNamespace(id=2002, name="학생B", email="b@example.com"),
        2003: SimpleNamespace(id=2003, name="학생C", email="c@example.com"),
    }

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return session_obj

    async def fake_list_session_members(_db, *, session_id):
        assert session_id == 44
        return [(member, users_by_id[member.student_user_id]) for member in member_state["items"]]

    async def fake_replace_session_members(_db, *, session_id, members):
        assert session_id == 44
        member_state["items"] = [
            SimpleNamespace(session_id=session_id, student_user_id=student_user_id, team_label=team_label)
            for student_user_id, team_label in members
        ]

    async def fake_update_session(_db, *, session, title):
        session.title = title
        return session

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_session_members", fake_list_session_members)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "replace_session_members", fake_replace_session_members)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "update_session", fake_update_session)

    get_result = asyncio.run(
        inspect.unwrap(peer_reviews.get_peer_review_session)(
            session_id=44,
            request=get_request,
            db=object(),
        )
    )
    assert get_result.title == "초기 제목"
    assert get_result.raw_text == "1조: 학생A, 학생B"
    assert len(get_result.members) == 2

    confirm_payload = SimpleNamespace(
        members=[
            SimpleNamespace(
                team_label="2조",
                raw_name="학생A",
                student_user_id=2001,
                student_name="학생A",
                student_email="a@example.com",
            ),
            SimpleNamespace(
                team_label="2조",
                raw_name="학생C",
                student_user_id=2003,
                student_name="학생C",
                student_email="c@example.com",
            ),
        ],
        unresolved_members=[],
    )

    confirm_result = asyncio.run(
        inspect.unwrap(peer_reviews.confirm_peer_review_members)(
            session_id=44,
            payload=confirm_payload,
            request=confirm_request,
            db=object(),
        )
    )
    assert {member.student_user_id for member in confirm_result.members} == {2001, 2003}

    update_result = asyncio.run(
        inspect.unwrap(peer_reviews.update_peer_review_session)(
            session_id=44,
            payload=SimpleNamespace(title="변경된 제목"),
            request=update_request,
            db=object(),
        )
    )
    assert update_result.title == "변경된 제목"
    assert update_result.raw_text == "2조: 학생A, 학생C"
    assert {member.student_user_id for member in update_result.members} == {2001, 2003}


def test_update_peer_review_session_requires_professor(monkeypatch):
    request = _make_request("/peer-reviews/sessions/33", method="PATCH")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["가천대학교"], email=email)

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.update_peer_review_session)(
                session_id=33,
                payload=SimpleNamespace(title="수정된 제목"),
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_update_peer_review_session_returns_404_for_missing_session(monkeypatch):
    request = _make_request("/peer-reviews/sessions/999", method="PATCH")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return None

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.update_peer_review_session)(
                session_id=999,
                payload=SimpleNamespace(title="수정된 제목"),
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_delete_peer_review_session_success(monkeypatch):
    request = _make_request("/peer-reviews/sessions/33", method="DELETE")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    session_obj = SimpleNamespace(id=33, professor_user_id=7)

    async def fake_get_session(*_args, **_kwargs):
        return session_obj

    deleted: dict[str, bool] = {"called": False}

    async def fake_delete_session(_db, *, session):
        assert session is session_obj
        deleted["called"] = True

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "delete_session", fake_delete_session)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.delete_peer_review_session)(
            session_id=33,
            request=request,
            db=object(),
        )
    )

    assert result.message == "Deleted"
    assert deleted["called"] is True


def test_delete_peer_review_session_requires_professor(monkeypatch):
    request = _make_request("/peer-reviews/sessions/33", method="DELETE")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["가천대학교"], email=email)

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.delete_peer_review_session)(
                session_id=33,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_delete_peer_review_session_returns_404_for_missing_session(monkeypatch):
    request = _make_request("/peer-reviews/sessions/999", method="DELETE")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return None

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.delete_peer_review_session)(
                session_id=999,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_update_session_status_success(monkeypatch):
    request = _make_request("/peer-reviews/sessions/33/status", method="PATCH")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return SimpleNamespace(
            id=33,
            title="중간고사",
            professor_user_id=7,
            is_open=True,
            access_token="token-33",
            raw_text="1조: 학생A",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def fake_update_session_is_open(_db, *, session, is_open):
        session.is_open = is_open
        return session

    async def fake_list_session_members(_db, *, session_id):
        assert session_id == 33
        return [
            (
                SimpleNamespace(session_id=33, student_user_id=1001, team_label="1조"),
                SimpleNamespace(id=1001, name="학생A", email="a@example.com"),
            )
        ]

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "update_session_is_open", fake_update_session_is_open)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_session_members", fake_list_session_members)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.update_peer_review_session_status)(
            session_id=33,
            payload=SimpleNamespace(is_open=False),
            request=request,
            db=object(),
        )
    )

    assert result.id == 33
    assert result.is_open is False
    assert result.raw_text == "1조: 학생A"
    assert len(result.members) == 1


def test_update_session_status_requires_professor(monkeypatch):
    request = _make_request("/peer-reviews/sessions/33/status", method="PATCH")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["가천대학교"], email=email)

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.update_peer_review_session_status)(
                session_id=33,
                payload=SimpleNamespace(is_open=False),
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_update_session_status_returns_404_for_missing_session(monkeypatch):
    request = _make_request("/peer-reviews/sessions/999/status", method="PATCH")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return None

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.update_peer_review_session_status)(
                session_id=999,
                payload=SimpleNamespace(is_open=True),
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_map_parsed_teams_to_students_returns_candidates_for_ambiguous_name():
    parsed_teams = [
        {
            "team_label": "1조",
            "members": [{"name": "김민", "email_hint": None}],
        }
    ]
    students = [
        SimpleNamespace(id=1, name="김민수", email="minsu@example.com"),
        SimpleNamespace(id=2, name="김민지", email="minji@example.com"),
    ]

    teams, unresolved = peer_reviews._map_parsed_teams_to_students(
        parsed_teams=parsed_teams,
        students=students,
    )

    assert teams == {}
    assert len(unresolved) == 1
    assert unresolved[0].reason == "ambiguous_name"
    assert [candidate.student_email for candidate in unresolved[0].candidates] == [
        "minsu@example.com",
        "minji@example.com",
    ]


def test_map_parsed_teams_to_students_handles_name_with_affiliation_suffix():
    parsed_teams = [
        {
            "team_label": "1조",
            "members": [{"name": "김남주/스타트업칼리지", "email_hint": None}],
        }
    ]
    students = [
        SimpleNamespace(id=10, name="김남주/스타트업칼리지", email="namjoo@example.com"),
    ]

    teams, unresolved = peer_reviews._map_parsed_teams_to_students(
        parsed_teams=parsed_teams,
        students=students,
    )

    assert unresolved == []
    assert "1조" in teams
    assert len(teams["1조"]) == 1
    assert teams["1조"][0].student_user_id == 10


def test_map_parsed_teams_to_students_marks_student_in_multiple_teams_unresolved():
    parsed_teams = [
        {
            "team_label": "1조",
            "members": [{"name": "홍길동", "email_hint": None}],
        },
        {
            "team_label": "2조",
            "members": [{"name": "홍길동", "email_hint": None}],
        },
    ]
    students = [
        SimpleNamespace(id=11, name="홍길동", email="hong@example.com"),
    ]

    teams, unresolved = peer_reviews._map_parsed_teams_to_students(
        parsed_teams=parsed_teams,
        students=students,
    )

    assert "1조" in teams
    assert len(teams["1조"]) == 1
    assert teams["1조"][0].student_user_id == 11

    assert len(unresolved) == 1
    assert unresolved[0].team_label == "2조"
    assert unresolved[0].raw_name == "홍길동"
    assert unresolved[0].reason == "student_in_multiple_teams"
    assert [candidate.student_user_id for candidate in unresolved[0].candidates] == [11]


def test_parse_peer_review_members_uses_copilot_parser(monkeypatch):
    request = _make_request("/peer-reviews/sessions/1/members:parse")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return SimpleNamespace(id=1, professor_user_id=7)

    async def fake_parse_team_text_with_copilot(*, raw_text, copilot):
        assert raw_text == "1조: 김남주/스타트업칼리지"
        assert copilot is sentinel_copilot
        return [
            {
                "team_label": "1조",
                "members": [{"name": "김남주/스타트업칼리지", "email_hint": None}],
            }
        ]

    async def fake_list_student_users(_db):
        return [
            SimpleNamespace(id=10, name="김남주/스타트업칼리지", email="namjoo@example.com"),
        ]

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)
    monkeypatch.setattr(peer_reviews, "_parse_team_text_with_copilot", fake_parse_team_text_with_copilot)
    monkeypatch.setattr(peer_reviews, "_list_student_users", fake_list_student_users)

    sentinel_copilot = object()
    payload = SimpleNamespace(raw_text="1조: 김남주/스타트업칼리지")

    result = asyncio.run(
        inspect.unwrap(peer_reviews.parse_peer_review_members)(
            session_id=1,
            payload=payload,
            request=request,
            db=object(),
            copilot=sentinel_copilot,
        )
    )

    assert "1조" in result.teams
    assert len(result.teams["1조"]) == 1
    assert result.teams["1조"][0].student_user_id == 10
    assert result.unresolved_members == []


def test_confirm_members_rejects_when_unresolved_members_exist(monkeypatch):
    request = _make_request("/peer-reviews/sessions/1/members:confirm")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return SimpleNamespace(id=1, professor_user_id=7)

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)

    payload = SimpleNamespace(
        members=[SimpleNamespace(student_user_id=101, team_label="1조")],
        unresolved_members=[
            SimpleNamespace(
                team_label="1조",
                raw_name="김민",
                reason="ambiguous_name",
                candidates=[
                    SimpleNamespace(student_user_id=1, student_name="김민수", student_email="minsu@example.com"),
                ],
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.confirm_peer_review_members)(
                session_id=1,
                payload=payload,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unresolved members must be resolved before confirmation"


def test_get_session_progress_returns_submission_statuses(monkeypatch):
    request = _make_request("/peer-reviews/sessions/77/progress", method="GET")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_session(*_args, **_kwargs):
        return SimpleNamespace(id=77, professor_user_id=7, is_open=False)

    async def fake_list_progress_rows(_db, *, session_id):
        assert session_id == 77
        return [
            (
                SimpleNamespace(team_label="1조"),
                SimpleNamespace(id=101, name="학생A", email="a@example.com"),
                True,
            ),
            (
                SimpleNamespace(team_label="1조"),
                SimpleNamespace(id=102, name="학생B", email="b@example.com"),
                False,
            ),
        ]

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_id_and_professor", fake_get_session)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_session_progress_rows", fake_list_progress_rows)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.get_peer_review_session_progress)(
            session_id=77,
            request=request,
            db=object(),
        )
    )

    assert result.session_id == 77
    assert result.is_open is False
    assert len(result.evaluator_statuses) == 2
    assert result.evaluator_statuses[0].has_submitted is True
    assert result.evaluator_statuses[1].has_submitted is False


def test_get_session_progress_requires_professor(monkeypatch):
    request = _make_request("/peer-reviews/sessions/77/progress", method="GET")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=7, roles=["가천대학교"], email=email)

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.get_peer_review_session_progress)(
                session_id=77,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_get_peer_review_my_summary_success(monkeypatch):
    request = _make_request("/peer-reviews/forms/token-77/my-summary", method="GET")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=101, roles=["가천대학교"], email=email)

    async def fake_get_session_by_access_token(_db, token):
        assert token == "token-77"
        return SimpleNamespace(id=77, is_open=True, title="중간고사")

    async def fake_get_member(_db, *, session_id, student_user_id):
        assert session_id == 77
        assert student_user_id == 101
        return SimpleNamespace(session_id=77, student_user_id=101, team_label="1조")

    async def fake_build_summary_for_user(_db, *, session_id, user_id):
        assert session_id == 77
        assert user_id == 101
        return {
            "my_received_contribution_avg": 26.5,
            "my_given_contribution_avg": 25.0,
            "my_fit_yes_ratio_received": 80.0,
            "my_fit_yes_ratio_given": 75.0,
        }

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_access_token", fake_get_session_by_access_token)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_member", fake_get_member)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "build_summary_for_user", fake_build_summary_for_user)

    result = asyncio.run(
        inspect.unwrap(peer_reviews.get_peer_review_my_summary)(
            token="token-77",
            request=request,
            db=object(),
        )
    )

    assert result.session_id == 77
    assert result.my_received_contribution_avg == 26.5
    assert result.my_given_contribution_avg == 25.0
    assert result.my_fit_yes_ratio_received == 80.0
    assert result.my_fit_yes_ratio_given == 75.0
