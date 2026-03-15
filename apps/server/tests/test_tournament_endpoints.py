import asyncio
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.routers import tournaments as _tournaments

tournaments = cast(Any, _tournaments)


def _make_request(path: str, method: str = "POST", email: str = "user@example.com") -> Request:
    async def receive() -> dict:
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


def _match_row(*, status: str = "open", is_bye: bool = False, vote_count_team1: int = 0, vote_count_team2: int = 0):
    now = datetime.now(timezone.utc)
    match = SimpleNamespace(
        id=101,
        session_id=55,
        bracket_type="main",
        round_no=1,
        match_no=1,
        status=status,
        is_bye=is_bye,
        team1_id=10,
        team2_id=20,
        winner_team_id=None,
        next_match_id=None,
        created_at=now,
        updated_at=now,
    )
    team1 = SimpleNamespace(id=10, name="A팀")
    team2 = SimpleNamespace(id=20, name="B팀")
    winner = None
    return (match, team1, team2, winner, vote_count_team1, vote_count_team2)


def test_list_tournament_sessions_requires_professor(monkeypatch):
    request = _make_request("/tournaments/sessions", method="GET", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "student@example.com"
        return SimpleNamespace(id=9, roles=["가천대학교"], email=email)

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(tournaments.list_tournament_sessions)(
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_list_tournament_sessions_success(monkeypatch):
    request = _make_request("/tournaments/sessions", method="GET", email="prof@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "prof@example.com"
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    now = datetime.now(timezone.utc)

    async def fake_list_sessions_by_professor(_db, *, professor_user_id):
        assert professor_user_id == 7
        return [
            (
                SimpleNamespace(
                    id=11,
                    title="토너먼트 A",
                    is_open=False,
                    created_at=now,
                    updated_at=now,
                ),
                4,
                7,
            )
        ]

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "list_sessions_by_professor", fake_list_sessions_by_professor)

    result = asyncio.run(
        inspect.unwrap(tournaments.list_tournament_sessions)(
            request=request,
            db=object(),
        )
    )

    assert result.total == 1
    assert result.items[0].id == 11
    assert result.items[0].team_count == 4
    assert result.items[0].match_count == 7


def test_submit_tournament_vote_rejects_closed_session(monkeypatch):
    request = _make_request("/tournaments/matches/101/vote", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=1001, roles=["가천대학교"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return _match_row(status="open", is_bye=False)

    async def fake_get_session_by_id(_db, session_id):
        assert session_id == 55
        return SimpleNamespace(id=55, is_open=False)

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments.tournament_crud, "get_session_by_id", fake_get_session_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(tournaments.submit_tournament_vote)(
                match_id=101,
                payload=SimpleNamespace(selected_team_id=10),
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Session is closed"


def test_submit_tournament_vote_rejects_non_open_match(monkeypatch):
    request = _make_request("/tournaments/matches/101/vote", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=1001, roles=["가천대학교"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return _match_row(status="closed", is_bye=False)

    async def fake_get_session_by_id(_db, session_id):
        return SimpleNamespace(id=session_id, is_open=True)

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments.tournament_crud, "get_session_by_id", fake_get_session_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(tournaments.submit_tournament_vote)(
                match_id=101,
                payload=SimpleNamespace(selected_team_id=10),
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Match is not open"


def test_submit_tournament_vote_rejects_bye_match(monkeypatch):
    request = _make_request("/tournaments/matches/101/vote", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=1001, roles=["가천대학교"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return _match_row(status="open", is_bye=True)

    async def fake_get_session_by_id(_db, session_id):
        return SimpleNamespace(id=session_id, is_open=True)

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments.tournament_crud, "get_session_by_id", fake_get_session_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(tournaments.submit_tournament_vote)(
                match_id=101,
                payload=SimpleNamespace(selected_team_id=10),
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Bye match does not accept votes"


def test_submit_tournament_vote_rejects_invalid_team(monkeypatch):
    request = _make_request("/tournaments/matches/101/vote", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=1001, roles=["가천대학교"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return _match_row(status="open", is_bye=False)

    async def fake_get_session_by_id(_db, session_id):
        return SimpleNamespace(id=session_id, is_open=True)

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments.tournament_crud, "get_session_by_id", fake_get_session_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(tournaments.submit_tournament_vote)(
                match_id=101,
                payload=SimpleNamespace(selected_team_id=999),
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Selected team is not in this match"


def test_submit_tournament_vote_success(monkeypatch):
    request = _make_request("/tournaments/matches/101/vote", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        return SimpleNamespace(id=1001, roles=["가천대학교"], email=email)

    calls = {"get_match_with_votes": 0}

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        calls["get_match_with_votes"] += 1
        if calls["get_match_with_votes"] == 1:
            return _match_row(status="open", is_bye=False, vote_count_team1=0, vote_count_team2=0)
        return _match_row(status="open", is_bye=False, vote_count_team1=1, vote_count_team2=0)

    async def fake_get_session_by_id(_db, session_id):
        assert session_id == 55
        return SimpleNamespace(id=55, is_open=True)

    captured: dict[str, int] = {}

    async def fake_upsert_match_vote(_db, *, match_id, voter_user_id, selected_team_id):
        captured["match_id"] = match_id
        captured["voter_user_id"] = voter_user_id
        captured["selected_team_id"] = selected_team_id

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments.tournament_crud, "get_session_by_id", fake_get_session_by_id)
    monkeypatch.setattr(tournaments.tournament_crud, "upsert_match_vote", fake_upsert_match_vote)

    result = asyncio.run(
        inspect.unwrap(tournaments.submit_tournament_vote)(
            match_id=101,
            payload=SimpleNamespace(selected_team_id=10),
            request=request,
            db=object(),
        )
    )

    assert captured == {
        "match_id": 101,
        "voter_user_id": 1001,
        "selected_team_id": 10,
    }
    assert result.message == "Submitted"
    assert result.match.vote_count_team1 is None
    assert result.match.vote_count_team2 is None


def test_get_tournament_match_masks_votes_when_open(monkeypatch):
    request = _make_request("/tournaments/matches/101", method="GET", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "student@example.com"
        return SimpleNamespace(id=9, roles=["가천대학교"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return _match_row(status="open", is_bye=False, vote_count_team1=2, vote_count_team2=1)

    async def fake_get_session_by_id(_db, session_id):
        assert session_id == 55
        return SimpleNamespace(id=55, is_open=True)

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments.tournament_crud, "get_session_by_id", fake_get_session_by_id)

    result = asyncio.run(
        inspect.unwrap(tournaments.get_tournament_match)(
            match_id=101,
            request=request,
            db=object(),
        )
    )

    assert result.vote_count_team1 is None
    assert result.vote_count_team2 is None


def test_get_tournament_match_returns_votes_when_closed(monkeypatch):
    request = _make_request("/tournaments/matches/101", method="GET", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "student@example.com"
        return SimpleNamespace(id=9, roles=["가천대학교"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return _match_row(status="closed", is_bye=False, vote_count_team1=2, vote_count_team2=1)

    async def fake_get_session_by_id(_db, session_id):
        assert session_id == 55
        return SimpleNamespace(id=55, is_open=False)

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments.tournament_crud, "get_session_by_id", fake_get_session_by_id)

    result = asyncio.run(
        inspect.unwrap(tournaments.get_tournament_match)(
            match_id=101,
            request=request,
            db=object(),
        )
    )

    assert result.vote_count_team1 == 2
    assert result.vote_count_team2 == 1


def test_get_tournament_match_progress_requires_professor(monkeypatch):
    request = _make_request("/tournaments/matches/101/progress", method="GET", email="student@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "student@example.com"
        return SimpleNamespace(id=9, roles=["가천대학교"], email=email)

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(tournaments.get_tournament_match_progress)(
                match_id=101,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_get_tournament_match_progress_not_found(monkeypatch):
    request = _make_request("/tournaments/matches/101/progress", method="GET", email="prof@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "prof@example.com"
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return None

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(tournaments.get_tournament_match_progress)(
                match_id=101,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Tournament match not found"


def test_get_tournament_match_progress_masks_votes_when_open(monkeypatch):
    request = _make_request("/tournaments/matches/101/progress", method="GET", email="prof@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "prof@example.com"
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return _match_row(status="open", is_bye=False, vote_count_team1=2, vote_count_team2=1)

    async def fake_get_professor_session_or_404(_db, *, session_id, professor_user_id):
        assert session_id == 55
        assert professor_user_id == 7
        return SimpleNamespace(id=55, is_open=True)

    async def fake_list_match_voter_statuses(_db, *, match_id):
        assert match_id == 101
        return [
            (1001, "홍길동", True),
            (1002, "김철수", False),
        ]

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments, "_get_professor_session_or_404", fake_get_professor_session_or_404)
    monkeypatch.setattr(tournaments.tournament_crud, "list_match_voter_statuses", fake_list_match_voter_statuses)

    result = asyncio.run(
        inspect.unwrap(tournaments.get_tournament_match_progress)(
            match_id=101,
            request=request,
            db=object(),
        )
    )

    assert result.match.id == 101
    assert result.match.vote_count_team1 is None
    assert result.match.vote_count_team2 is None
    assert result.vote_url == "/tournaments/matches/101/vote"
    assert result.session_is_open is True
    assert result.submitted_count == 1
    assert result.total_count == 2
    assert result.voter_statuses[0].voter_name == "홍길동"
    assert result.voter_statuses[0].has_submitted is True
    assert result.voter_statuses[1].has_submitted is False


def test_get_tournament_match_progress_returns_votes_when_closed(monkeypatch):
    request = _make_request("/tournaments/matches/101/progress", method="GET", email="prof@example.com")

    async def fake_get_user_by_email_basic(_db, email):
        assert email == "prof@example.com"
        return SimpleNamespace(id=7, roles=["교수"], email=email)

    async def fake_get_match_with_votes(_db, *, match_id):
        assert match_id == 101
        return _match_row(status="closed", is_bye=False, vote_count_team1=3, vote_count_team2=2)

    async def fake_get_professor_session_or_404(_db, *, session_id, professor_user_id):
        assert session_id == 55
        assert professor_user_id == 7
        return SimpleNamespace(id=55, is_open=False)

    async def fake_list_match_voter_statuses(_db, *, match_id):
        assert match_id == 101
        return []

    monkeypatch.setattr(tournaments.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(tournaments.tournament_crud, "get_match_with_votes", fake_get_match_with_votes)
    monkeypatch.setattr(tournaments, "_get_professor_session_or_404", fake_get_professor_session_or_404)
    monkeypatch.setattr(tournaments.tournament_crud, "list_match_voter_statuses", fake_list_match_voter_statuses)

    result = asyncio.run(
        inspect.unwrap(tournaments.get_tournament_match_progress)(
            match_id=101,
            request=request,
            db=object(),
        )
    )

    assert result.match.vote_count_team1 == 3
    assert result.match.vote_count_team2 == 2
    assert result.session_is_open is False
