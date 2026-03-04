import asyncio
import inspect
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from app import crud, schemas
from app.core.config import settings
from app.dependencies import get_active_user, verify_csrf
from app.main import app
from app.routers import mcp


def _limit_count(limit_rule: str) -> int:
    return int(limit_rule.split("/", 1)[0])


def _reset_rate_limiter_state() -> None:
    limiter_instance = getattr(app.state, "limiter", None)
    if limiter_instance is None:
        return

    for attr_name in ("_storage", "storage"):
        storage = getattr(limiter_instance, attr_name, None)
        if storage is None or not hasattr(storage, "reset"):
            continue

        result = storage.reset()
        if inspect.isawaitable(result):
            asyncio.run(result)
        return


@contextmanager
def _client_with_overrides(overrides: dict):
    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.update(overrides)
    _reset_rate_limiter_state()

    try:
        with TestClient(app, base_url="http://localhost") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        _reset_rate_limiter_state()


def test_tokens_create_rate_limit_returns_429_after_threshold(monkeypatch):
    async def fake_active_user():
        return SimpleNamespace(id=1, team_id=None, league_type=schemas.LeagueType.NONE, roles=["gcs"])

    async def fake_create_api_token(db, user_id, description, idempotency_key):
        return (
            SimpleNamespace(
                id=500,
                description=description,
                created_at=datetime(2026, 2, 27, 13, 30, tzinfo=timezone.utc),
                last_used_at=None,
            ),
            "raw-token",
        )

    monkeypatch.setattr(crud, "create_api_token", fake_create_api_token)

    with _client_with_overrides({verify_csrf: lambda: None, get_active_user: fake_active_user}) as client:
        limit_count = _limit_count(settings.TOKENS_WRITE_LIMIT)

        for idx in range(limit_count):
            response = client.post("/auth/tokens", json={"description": f"token-{idx}"})
            assert response.status_code == 200

        blocked = client.post("/auth/tokens", json={"description": "token-blocked"})
        assert blocked.status_code == 429


def test_teams_patch_rate_limit_returns_429_after_threshold(monkeypatch):
    async def fake_active_user():
        return SimpleNamespace(id=1, team_id=10, league_type=schemas.LeagueType.NONE, roles=["gcs"])

    async def fake_get_team_by_id(db, team_id):
        return SimpleNamespace(
            id=team_id,
            name="Rate Team",
            invite_code="RATE0001",
            league_type="none",
            created_at=datetime(2026, 2, 27, 13, 40, tzinfo=timezone.utc),
            members=[],
        )

    async def fake_update_team(db, team, league_type=None, name=None):
        return SimpleNamespace(
            id=team.id,
            name=name or team.name,
            invite_code=team.invite_code,
            league_type=league_type or team.league_type,
            created_at=team.created_at,
            members=[],
        )

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)
    monkeypatch.setattr(crud, "update_team", fake_update_team)

    with _client_with_overrides({verify_csrf: lambda: None, get_active_user: fake_active_user}) as client:
        limit_count = _limit_count(settings.TEAMS_WRITE_LIMIT)

        for idx in range(limit_count):
            response = client.patch("/teams/me", json={"name": f"Rate Team {idx}"})
            assert response.status_code == 200

        blocked = client.patch("/teams/me", json={"name": "Rate Team blocked"})
        assert blocked.status_code == 429


def test_users_patch_rate_limit_returns_429_after_threshold(monkeypatch):
    async def fake_active_user():
        return SimpleNamespace(id=1, team_id=None, league_type=schemas.LeagueType.NONE, roles=["gcs"])

    async def fake_update_user_league_type(db, user, league_type):
        return SimpleNamespace(league_type=league_type)

    monkeypatch.setattr(crud, "update_user_league_type", fake_update_user_league_type)

    with _client_with_overrides({verify_csrf: lambda: None, get_active_user: fake_active_user}) as client:
        limit_count = _limit_count(settings.USERS_LEAGUE_UPDATE_LIMIT)

        for _ in range(limit_count):
            response = client.patch("/users/me/league", json={"league_type": "semester"})
            assert response.status_code == 200

        blocked = client.patch("/users/me/league", json={"league_type": "semester"})
        assert blocked.status_code == 429


def test_mcp_post_rate_limit_enforcer_returns_429_after_threshold():
    from starlette.requests import Request

    limit_count = _limit_count(settings.MCP_HTTP_MESSAGES_LIMIT)

    def make_request() -> Request:
        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/mcp",
                "headers": [],
                "query_string": b"",
                "client": ("127.0.0.1", 12345),
            },
            receive=receive,
        )

    _reset_rate_limiter_state()

    try:
        for _ in range(limit_count):
            asyncio.run(mcp._enforce_mcp_mutation_limit(request=make_request()))

        with pytest.raises(RateLimitExceeded):
            asyncio.run(mcp._enforce_mcp_mutation_limit(request=make_request()))
    finally:
        _reset_rate_limiter_state()
