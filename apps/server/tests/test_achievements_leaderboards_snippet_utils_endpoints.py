import asyncio
from datetime import date, datetime, timedelta, timezone
import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import crud, schemas
from app.routers import achievements, leaderboards, snippet_utils


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


def test_achievements_me_returns_items_and_total(monkeypatch):
    user = SimpleNamespace(id=10)
    rows = [
        {
            "achievement_definition_id": 1,
            "code": "daily_submitted",
            "name": "Daily Submitted",
            "description": "desc",
            "badge_image_url": "url",
            "rarity": "common",
            "grant_count": 2,
            "last_granted_at": datetime(2026, 2, 27, 13, 0, tzinfo=timezone.utc),
        }
    ]

    async def fake_list_my_achievement_groups(db, user_id):
        assert user_id == 10
        return rows

    monkeypatch.setattr(crud, "list_my_achievement_groups", fake_list_my_achievement_groups)

    result = asyncio.run(inspect.unwrap(achievements.get_my_achievements)(db=object(), user=user))

    assert result["items"] == rows
    assert result["total"] == 1


def test_achievements_recent_respects_limit(monkeypatch):
    request = _make_request(path="/achievements/recent", method="GET")
    user = SimpleNamespace(id=1)
    now = datetime(2026, 2, 27, 13, 10, tzinfo=timezone.utc)

    captured: dict[str, object] = {}

    async def fake_list_recent_public_achievement_grants(db, now, limit):
        captured["limit"] = limit
        captured["now"] = now
        return ([{"grant_id": 1}], 7)

    monkeypatch.setattr(achievements, "get_request_now", lambda _req: now)
    monkeypatch.setattr(crud, "list_recent_public_achievement_grants", fake_list_recent_public_achievement_grants)

    result = asyncio.run(
        inspect.unwrap(achievements.get_recent_achievements)(
            request=request,
            limit=5,
            db=object(),
            user=user,
        )
    )

    assert captured["limit"] == 5
    assert captured["now"] == now
    assert result == {"items": [{"grant_id": 1}], "total": 7, "limit": 5}


def test_snippet_date_returns_business_date(monkeypatch):
    request = _make_request(path="/snippet_date", method="GET")

    monkeypatch.setattr(snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 8, 30, tzinfo=timezone.utc))
    monkeypatch.setattr(snippet_utils, "current_business_date", lambda _now: date(2026, 2, 27))

    result = asyncio.run(inspect.unwrap(snippet_utils.get_snippet_date)(request=request))

    assert result == {"date": date(2026, 2, 27)}


def test_leaderboards_team_not_found_returns_404(monkeypatch):
    request = _make_request(path="/leaderboards", method="GET")
    user = SimpleNamespace(id=1, team_id=88, league_type=schemas.LeagueType.UNDERGRAD)

    monkeypatch.setattr(leaderboards.snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 13, 0, tzinfo=timezone.utc))

    async def fake_get_team_by_id(db, team_id):
        return None

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(leaderboards.get_leaderboard)(
                request=request,
                period="daily",
                limit=20,
                offset=0,
                db=object(),
                user=user,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Team not found"


def test_leaderboards_team_excluded_when_league_none(monkeypatch):
    request = _make_request(path="/leaderboards", method="GET")
    user = SimpleNamespace(id=1, team_id=3, league_type=schemas.LeagueType.UNDERGRAD)

    monkeypatch.setattr(leaderboards.snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 13, 0, tzinfo=timezone.utc))

    async def fake_get_team_by_id(db, team_id):
        return SimpleNamespace(id=3, league_type=schemas.LeagueType.NONE.value)

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)

    result = asyncio.run(
        inspect.unwrap(leaderboards.get_leaderboard)(
            request=request,
            period="daily",
            limit=20,
            offset=0,
            db=object(),
            user=user,
        )
    )

    assert result["excluded_by_league"] is True
    assert result["items"] == []
    assert result["total"] == 0
    assert result["league_type"] == schemas.LeagueType.NONE.value


def test_leaderboards_team_success_and_limit_offset(monkeypatch):
    request = _make_request(path="/leaderboards", method="GET")
    user = SimpleNamespace(id=1, team_id=3, league_type=schemas.LeagueType.NONE)
    now = datetime(2026, 2, 27, 13, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(leaderboards.snippet_utils, "get_request_now", lambda _req: now)

    async def fake_get_team_by_id(db, team_id):
        return SimpleNamespace(id=3, league_type=schemas.LeagueType.SEMESTER.value)

    async def fake_build_team_leaderboard(db, league_type, period, target_key):
        assert league_type == schemas.LeagueType.SEMESTER.value
        assert period == "weekly"
        assert target_key == date(2026, 2, 16)
        return [
            {
                "rank": 1,
                "score": 98.0,
                "participant_type": "team",
                "participant_id": 31,
                "participant_name": "A",
                "member_count": 2,
                "submitted_count": 2,
            },
            {
                "rank": 2,
                "score": 91.0,
                "participant_type": "team",
                "participant_id": 32,
                "participant_name": "B",
                "member_count": 2,
                "submitted_count": 1,
            },
            {
                "rank": 3,
                "score": 89.0,
                "participant_type": "team",
                "participant_id": 33,
                "participant_name": "C",
                "member_count": 2,
                "submitted_count": 1,
            },
        ]

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)
    monkeypatch.setattr(crud, "build_team_leaderboard", fake_build_team_leaderboard)

    result = asyncio.run(
        inspect.unwrap(leaderboards.get_leaderboard)(
            request=request,
            period="weekly",
            limit=2,
            offset=1,
            db=object(),
            user=user,
        )
    )

    assert result["excluded_by_league"] is False
    assert result["window"]["label"] == "last_week"
    assert result["window"]["key"] == date(2026, 2, 16)
    assert result["total"] == 3
    assert [item["participant_id"] for item in result["items"]] == [32, 33]


def test_leaderboards_individual_excluded_when_none(monkeypatch):
    request = _make_request(path="/leaderboards", method="GET")
    user = SimpleNamespace(id=1, team_id=None, league_type=schemas.LeagueType.NONE.value)

    monkeypatch.setattr(leaderboards.snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 13, 0, tzinfo=timezone.utc))

    result = asyncio.run(
        inspect.unwrap(leaderboards.get_leaderboard)(
            request=request,
            period="daily",
            limit=10,
            offset=0,
            db=object(),
            user=user,
        )
    )

    assert result["excluded_by_league"] is True
    assert result["items"] == []
    assert result["total"] == 0


def test_leaderboards_individual_success(monkeypatch):
    request = _make_request(path="/leaderboards", method="GET")
    user = SimpleNamespace(id=1, team_id=None, league_type=schemas.LeagueType.UNDERGRAD.value)

    monkeypatch.setattr(leaderboards.snippet_utils, "get_request_now", lambda _req: datetime(2026, 2, 27, 13, 0, tzinfo=timezone.utc))

    async def fake_build_individual_leaderboard(db, league_type, period, target_key):
        assert league_type == schemas.LeagueType.UNDERGRAD.value
        assert period == "daily"
        assert target_key == date(2026, 2, 26)
        return [
            {
                "rank": 1,
                "score": 95.0,
                "participant_type": "individual",
                "participant_id": 100,
                "participant_name": "Alice",
            }
        ]

    monkeypatch.setattr(crud, "build_individual_leaderboard", fake_build_individual_leaderboard)

    result = asyncio.run(
        inspect.unwrap(leaderboards.get_leaderboard)(
            request=request,
            period="daily",
            limit=20,
            offset=0,
            db=object(),
            user=user,
        )
    )

    assert result["excluded_by_league"] is False
    assert result["total"] == 1
    assert result["items"][0]["participant_name"] == "Alice"
