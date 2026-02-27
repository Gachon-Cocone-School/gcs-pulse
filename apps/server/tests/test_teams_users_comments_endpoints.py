import asyncio
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from sqlalchemy.exc import IntegrityError

from app import crud, schemas
from app.routers import comments, teams, users


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


class DummyDB:
    def __init__(self):
        self.added: list[object] = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.refresh_calls: list[object] = []
        self.raise_integrity_once = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1
        latest = self.added[-1] if self.added else None
        if latest is not None and getattr(latest, "id", None) is None:
            latest.id = 500 + self.flush_calls
        if self.raise_integrity_once:
            self.raise_integrity_once = False
            raise IntegrityError("statement", "params", Exception("duplicate"))

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1

    async def refresh(self, obj):
        self.refresh_calls.append(obj)


def test_teams_get_my_team_without_team_returns_none():
    user = SimpleNamespace(id=1, team_id=None)

    result = asyncio.run(inspect.unwrap(teams.get_my_team)(db=object(), user=user))

    assert result.team is None


def test_teams_create_team_success_with_retry_on_duplicate_code(monkeypatch):
    db = DummyDB()
    db.raise_integrity_once = True
    user = SimpleNamespace(id=1, team_id=None)
    codes = iter(["DUPL0001", "UNIQ0002"])
    loaded_team = SimpleNamespace(
        id=777,
        name="Alpha Team",
        invite_code="UNIQ0002",
        league_type="none",
        created_at=datetime(2026, 2, 27, 11, 0, tzinfo=timezone.utc),
        members=[],
    )

    monkeypatch.setattr(crud, "generate_invite_code", lambda: next(codes))

    async def fake_get_team_with_members(db_arg, team_id):
        assert team_id == user.team_id
        return loaded_team

    monkeypatch.setattr(crud, "get_team_with_members", fake_get_team_with_members)

    payload = schemas.TeamCreate(name="Alpha Team")
    result = asyncio.run(
        inspect.unwrap(teams.create_team)(
            payload=payload,
            request=_make_request(path="/teams", method="POST"),
            db=db,
            user=user,
        )
    )

    assert result.id == 777
    assert user.team_id == 502
    assert db.rollback_calls == 1
    assert db.commit_calls == 1


def test_teams_create_team_conflict_when_user_already_in_team():
    user = SimpleNamespace(id=1, team_id=9)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(teams.create_team)(
                payload=schemas.TeamCreate(name="New Team"),
                request=_make_request(path="/teams", method="POST"),
                db=DummyDB(),
                user=user,
            )
        )

    assert exc_info.value.status_code == 409


def test_teams_join_team_not_found_returns_404(monkeypatch):
    user = SimpleNamespace(id=10, team_id=None)

    async def fake_get_team_by_invite_code(db, code):
        assert code == "MISSING"
        return None

    monkeypatch.setattr(crud, "get_team_by_invite_code", fake_get_team_by_invite_code)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(teams.join_team)(
                payload=schemas.TeamJoin(invite_code="missing"),
                request=_make_request(path="/teams/join", method="POST"),
                db=DummyDB(),
                user=user,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Team not found"


def test_teams_join_team_success(monkeypatch):
    db = DummyDB()
    user = SimpleNamespace(id=10, team_id=None)
    team = SimpleNamespace(id=50)
    team_loaded = SimpleNamespace(
        id=50,
        name="Joined Team",
        invite_code="JOIN0001",
        league_type="none",
        created_at=datetime(2026, 2, 27, 11, 30, tzinfo=timezone.utc),
        members=[],
    )

    async def fake_get_team_by_invite_code(db_arg, code):
        assert code == "JOIN0001"
        return team

    async def fake_get_team_with_members(db_arg, team_id):
        assert team_id == 50
        return team_loaded

    monkeypatch.setattr(crud, "get_team_by_invite_code", fake_get_team_by_invite_code)
    monkeypatch.setattr(crud, "get_team_with_members", fake_get_team_with_members)

    result = asyncio.run(
        inspect.unwrap(teams.join_team)(
            payload=schemas.TeamJoin(invite_code="join0001"),
            request=_make_request(path="/teams/join", method="POST"),
            db=db,
            user=user,
        )
    )

    assert result.id == 50
    assert user.team_id == 50
    assert db.commit_calls == 1
    assert db.refresh_calls == [user]


def test_teams_leave_team_not_in_team_returns_400():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(teams.leave_team)(
                request=_make_request(path="/teams/leave", method="POST"),
                db=DummyDB(),
                user=SimpleNamespace(id=1, team_id=None),
            )
        )

    assert exc_info.value.status_code == 400


def test_teams_leave_team_deletes_empty_team(monkeypatch):
    db = DummyDB()
    user = SimpleNamespace(id=11, team_id=9)
    team = SimpleNamespace(id=9)
    captured: dict[str, object] = {}

    async def fake_get_team_by_id(db_arg, team_id):
        return team

    async def fake_count_team_members(db_arg, team_id):
        return 0

    async def fake_delete_team(db_arg, team_arg):
        captured["deleted_team"] = team_arg

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)
    monkeypatch.setattr(crud, "count_team_members", fake_count_team_members)
    monkeypatch.setattr(crud, "delete_team", fake_delete_team)

    result = asyncio.run(
        inspect.unwrap(teams.leave_team)(
            request=_make_request(path="/teams/leave", method="POST"),
            db=db,
            user=user,
        )
    )

    assert result == {"message": "Left team"}
    assert user.team_id is None
    assert captured["deleted_team"] is team


def test_teams_rename_requires_name_when_none():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(teams.rename_my_team)(
                payload=schemas.TeamUpdate(name=None),
                request=_make_request(path="/teams/me", method="PATCH"),
                db=DummyDB(),
                user=SimpleNamespace(id=1, team_id=10),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Team name is required"


def test_teams_update_league_team_not_found_returns_404(monkeypatch):
    async def fake_get_team_by_id(db, team_id):
        return None

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(teams.update_my_team_league)(
                payload=schemas.LeagueUpdate(league_type=schemas.LeagueType.SEMESTER),
                request=_make_request(path="/teams/me/league", method="PATCH"),
                db=DummyDB(),
                user=SimpleNamespace(id=1, team_id=222),
            )
        )

    assert exc_info.value.status_code == 404


def test_teams_update_league_success(monkeypatch):
    user = SimpleNamespace(id=1, team_id=222)
    db_team = SimpleNamespace(id=222, league_type="none")
    updated_team = SimpleNamespace(
        id=222,
        name="Team Z",
        invite_code="TEAMZ",
        league_type="semester",
        created_at=datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc),
        members=[],
    )

    async def fake_get_team_by_id(db, team_id):
        return db_team

    async def fake_update_team(db, team, league_type=None, name=None):
        assert league_type == "semester"
        return updated_team

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)
    monkeypatch.setattr(crud, "update_team", fake_update_team)

    result = asyncio.run(
        inspect.unwrap(teams.update_my_team_league)(
            payload=schemas.LeagueUpdate(league_type=schemas.LeagueType.SEMESTER),
            request=_make_request(path="/teams/me/league", method="PATCH"),
            db=DummyDB(),
            user=user,
        )
    )

    assert result.id == 222
    assert result.league_type == schemas.LeagueType.SEMESTER


def test_users_get_my_league_team_not_found_returns_404(monkeypatch):
    user = SimpleNamespace(id=1, team_id=999, league_type=schemas.LeagueType.UNDERGRAD)

    async def fake_get_team_by_id(db, team_id):
        return None

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(inspect.unwrap(users.get_my_league)(db=object(), user=user))

    assert exc_info.value.status_code == 404


def test_users_get_my_league_personal_returns_updatable():
    user = SimpleNamespace(id=1, team_id=None, league_type=schemas.LeagueType.UNDERGRAD)

    result = asyncio.run(inspect.unwrap(users.get_my_league)(db=object(), user=user))

    assert result == {
        "league_type": schemas.LeagueType.UNDERGRAD,
        "can_update": True,
        "managed_by_team": False,
    }


def test_users_patch_my_league_blocks_team_members():
    user = SimpleNamespace(id=1, team_id=5, league_type=schemas.LeagueType.NONE)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(users.update_my_league)(
                payload=schemas.LeagueUpdate(league_type=schemas.LeagueType.SEMESTER),
                request=_make_request(path="/users/me/league", method="PATCH"),
                db=object(),
                user=user,
            )
        )

    assert exc_info.value.status_code == 409


def test_users_patch_my_league_success(monkeypatch):
    user = SimpleNamespace(id=1, team_id=None, league_type=schemas.LeagueType.NONE)

    async def fake_update_user_league_type(db, user_arg, league_type):
        return SimpleNamespace(league_type=league_type)

    monkeypatch.setattr(crud, "update_user_league_type", fake_update_user_league_type)

    result = asyncio.run(
        inspect.unwrap(users.update_my_league)(
            payload=schemas.LeagueUpdate(league_type=schemas.LeagueType.SEMESTER),
            request=_make_request(path="/users/me/league", method="PATCH"),
            db=object(),
            user=user,
        )
    )

    assert result == {
        "league_type": "semester",
        "can_update": True,
        "managed_by_team": False,
    }


def test_comments_create_requires_exactly_one_snippet_id(monkeypatch):
    async def fake_viewer(request, db, include_consents=False):
        return SimpleNamespace(id=1, team_id=1)

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(comments.create_comment)(
                request=_make_request("/comments", "POST"),
                payload=schemas.CommentCreate(content="hello", daily_snippet_id=1, weekly_snippet_id=2),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400


def test_comments_create_daily_snippet_not_found_returns_404(monkeypatch):
    async def fake_viewer(request, db, include_consents=False):
        return SimpleNamespace(id=1, team_id=1)

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return None

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(comments.create_comment)(
                request=_make_request("/comments", "POST"),
                payload=schemas.CommentCreate(content="hello", daily_snippet_id=10),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404


def test_comments_create_weekly_access_denied_returns_403(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=2, team_id=2)
    weekly_snippet = SimpleNamespace(id=5, user=owner)

    async def fake_viewer(request, db, include_consents=False):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return weekly_snippet

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(comments.snippet_utils, "can_read_snippet", lambda _v, _o: False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(comments.create_comment)(
                request=_make_request("/comments", "POST"),
                payload=schemas.CommentCreate(content="hello", weekly_snippet_id=5),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_comments_create_success(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=1)
    owner = SimpleNamespace(id=2, team_id=1)
    daily_snippet = SimpleNamespace(id=8, user=owner)

    async def fake_viewer(request, db, include_consents=False):
        return viewer

    async def fake_get_daily_snippet_by_id(db, snippet_id):
        return daily_snippet

    async def fake_create_comment(db, user_id, content, daily_snippet_id=None, weekly_snippet_id=None):
        return SimpleNamespace(
            id=100,
            user_id=user_id,
            content=content,
            daily_snippet_id=daily_snippet_id,
            weekly_snippet_id=weekly_snippet_id,
            created_at=datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc),
            user=None,
        )

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)
    monkeypatch.setattr(crud, "get_daily_snippet_by_id", fake_get_daily_snippet_by_id)
    monkeypatch.setattr(comments.snippet_utils, "can_read_snippet", lambda _v, _o: True)
    monkeypatch.setattr(crud, "create_comment", fake_create_comment)

    result = asyncio.run(
        inspect.unwrap(comments.create_comment)(
            request=_make_request("/comments", "POST"),
            payload=schemas.CommentCreate(content="nice", daily_snippet_id=8),
            db=object(),
        )
    )

    assert result.id == 100
    assert result.daily_snippet_id == 8


def test_comments_list_requires_one_selector(monkeypatch):
    async def fake_viewer(request, db, include_consents=False):
        return SimpleNamespace(id=1, team_id=1)

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(comments.list_comments)(
                request=_make_request("/comments", "GET"),
                daily_snippet_id=None,
                weekly_snippet_id=None,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400


def test_comments_list_weekly_success(monkeypatch):
    viewer = SimpleNamespace(id=1, team_id=2)
    owner = SimpleNamespace(id=4, team_id=2)
    weekly_snippet = SimpleNamespace(id=7, user=owner)

    async def fake_viewer(request, db, include_consents=False):
        return viewer

    async def fake_get_weekly_snippet_by_id(db, snippet_id):
        return weekly_snippet

    async def fake_list_comments(db, daily_snippet_id=None, weekly_snippet_id=None):
        return [
            SimpleNamespace(
                id=91,
                user_id=viewer.id,
                user=None,
                content="comment",
                daily_snippet_id=daily_snippet_id,
                weekly_snippet_id=weekly_snippet_id,
                created_at=datetime(2026, 2, 27, 12, 30, tzinfo=timezone.utc),
                updated_at=datetime(2026, 2, 27, 12, 30, tzinfo=timezone.utc),
            )
        ]

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)
    monkeypatch.setattr(crud, "get_weekly_snippet_by_id", fake_get_weekly_snippet_by_id)
    monkeypatch.setattr(comments.snippet_utils, "can_read_snippet", lambda _v, _o: True)
    monkeypatch.setattr(crud, "list_comments", fake_list_comments)

    result = asyncio.run(
        inspect.unwrap(comments.list_comments)(
            request=_make_request("/comments", "GET"),
            daily_snippet_id=None,
            weekly_snippet_id=7,
            db=object(),
        )
    )

    assert len(result) == 1
    assert result[0].id == 91


def test_comments_update_not_authorized_returns_403(monkeypatch):
    viewer = SimpleNamespace(id=2)
    comment_row = SimpleNamespace(id=33, user_id=1)

    async def fake_viewer(request, db, include_consents=False):
        return viewer

    async def fake_get_comment_by_id(db, comment_id):
        return comment_row

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)
    monkeypatch.setattr(crud, "get_comment_by_id", fake_get_comment_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(comments.update_comment)(
                comment_id=33,
                payload=schemas.CommentUpdate(content="updated"),
                request=_make_request("/comments/33", "PUT"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_comments_update_success(monkeypatch):
    viewer = SimpleNamespace(id=2)
    comment_row = SimpleNamespace(id=33, user_id=2)

    async def fake_viewer(request, db, include_consents=False):
        return viewer

    async def fake_get_comment_by_id(db, comment_id):
        return comment_row

    async def fake_update_comment(db, comment, content):
        return SimpleNamespace(
            id=comment.id,
            user_id=comment.user_id,
            user=None,
            content=content,
            daily_snippet_id=None,
            weekly_snippet_id=7,
            created_at=datetime(2026, 2, 27, 12, 40, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 27, 12, 41, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)
    monkeypatch.setattr(crud, "get_comment_by_id", fake_get_comment_by_id)
    monkeypatch.setattr(crud, "update_comment", fake_update_comment)

    result = asyncio.run(
        inspect.unwrap(comments.update_comment)(
            comment_id=33,
            payload=schemas.CommentUpdate(content="updated"),
            request=_make_request("/comments/33", "PUT"),
            db=object(),
        )
    )

    assert result.id == 33
    assert result.content == "updated"


def test_comments_delete_forbidden_returns_403(monkeypatch):
    viewer = SimpleNamespace(id=2)
    comment_row = SimpleNamespace(id=44, user_id=1)

    async def fake_viewer(request, db, include_consents=False):
        return viewer

    async def fake_get_comment_by_id(db, comment_id):
        return comment_row

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)
    monkeypatch.setattr(crud, "get_comment_by_id", fake_get_comment_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(comments.delete_comment)(
                comment_id=44,
                request=_make_request("/comments/44", "DELETE"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 403


def test_comments_delete_success(monkeypatch):
    viewer = SimpleNamespace(id=2)
    comment_row = SimpleNamespace(id=44, user_id=2)
    deleted: dict[str, int] = {}

    async def fake_viewer(request, db, include_consents=False):
        return viewer

    async def fake_get_comment_by_id(db, comment_id):
        return comment_row

    async def fake_delete_comment(db, comment):
        deleted["id"] = comment.id

    monkeypatch.setattr(comments.snippet_utils, "get_viewer_or_401", fake_viewer)
    monkeypatch.setattr(crud, "get_comment_by_id", fake_get_comment_by_id)
    monkeypatch.setattr(crud, "delete_comment", fake_delete_comment)

    result = asyncio.run(
        inspect.unwrap(comments.delete_comment)(
            comment_id=44,
            request=_make_request("/comments/44", "DELETE"),
            db=object(),
        )
    )

    assert result == {"message": "Comment deleted"}
    assert deleted["id"] == 44
