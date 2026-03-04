import asyncio
import inspect

import pytest
from fastapi import HTTPException
from fastapi.params import Depends as DependsParam
from fastapi.testclient import TestClient
from mcp.server.streamable_http import MCP_PROTOCOL_VERSION_HEADER, MCP_SESSION_ID_HEADER
from starlette.requests import Request

from app import crud
from app.main import app
from app.routers import mcp, snippet_utils


class DummyUser:
    def __init__(self, user_id: int, roles=None):
        self.id = user_id
        self.roles = roles or ["gcs"]


class DummyToken:
    def __init__(self, user_id: int):
        self.user_id = user_id


def _make_request(
    path: str,
    method: str,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> Request:
    encoded_headers = [
        (key.lower().encode("utf-8"), value.encode("utf-8"))
        for key, value in (headers or {}).items()
    ]

    body_sent = False

    async def receive() -> dict:
        nonlocal body_sent
        if body_sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        body_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": encoded_headers,
        "query_string": b"",
    }
    return Request(scope, receive=receive)


def _base_mcp_headers() -> dict[str, str]:
    return {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
    }


def _patch_mcp_auth_bypass(monkeypatch) -> None:
    async def fake_get_mcp_user_from_bearer(request, db):
        user = DummyUser(user_id=1, roles=["gcs"])
        user.email = "user@example.com"
        user.name = "User"
        user.team_id = None
        user.league_type = "none"
        return snippet_utils.BearerAuthContext(
            user=user,
            api_token=DummyToken(user_id=1),
        )

    monkeypatch.setattr(mcp, "get_mcp_user_from_bearer", fake_get_mcp_user_from_bearer)


def test_mcp_bearer_dependency_uses_same_auth_dependency():
    signature = inspect.signature(inspect.unwrap(mcp.get_mcp_user_from_bearer))
    db_default = signature.parameters["db"].default
    assert isinstance(db_default, DependsParam)
    assert db_default.dependency is mcp.get_db


def test_bearer_auth_missing_token_returns_401():
    request = _make_request(path="/mcp", method="GET")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(snippet_utils.get_bearer_auth_or_401(request=request, db=object()))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API token"


def test_bearer_auth_invalid_token_returns_401(monkeypatch):
    request = _make_request(
        path="/mcp",
        method="GET",
        headers={"authorization": "Bearer invalid-token"},
    )

    async def fake_get_api_token_by_raw_token(db, raw_token):
        return None

    monkeypatch.setattr(crud, "get_api_token_by_raw_token", fake_get_api_token_by_raw_token)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(snippet_utils.get_bearer_auth_or_401(request=request, db=object()))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API token"


def test_bearer_auth_valid_token_touches_last_used_at(monkeypatch):
    request = _make_request(
        path="/mcp",
        method="GET",
        headers={"authorization": "Bearer valid-token"},
    )

    token = DummyToken(user_id=101)
    user = DummyUser(user_id=101)
    captured: dict[str, object] = {}

    async def fake_get_api_token_by_raw_token(db, raw_token):
        captured["raw_token"] = raw_token
        return token

    async def fake_get_user_by_id(db, user_id):
        captured["user_id"] = user_id
        return user

    async def fake_touch_api_token_last_used_at(db, db_token, used_at=None):
        captured["touch_called"] = True
        captured["touched_token"] = db_token
        return db_token

    monkeypatch.setattr(crud, "get_api_token_by_raw_token", fake_get_api_token_by_raw_token)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(crud, "touch_api_token_last_used_at", fake_touch_api_token_last_used_at)

    auth_context = asyncio.run(snippet_utils.get_bearer_auth_or_401(request=request, db=object()))

    assert auth_context.user is user
    assert auth_context.api_token is token
    assert captured["raw_token"] == "valid-token"
    assert captured["user_id"] == 101
    assert captured["touch_called"] is True
    assert captured["touched_token"] is token


def test_bearer_auth_plain_user_role_returns_403(monkeypatch):
    request = _make_request(
        path="/mcp",
        method="GET",
        headers={"authorization": "Bearer valid-token"},
    )

    async def fake_get_api_token_by_raw_token(db, raw_token):
        return DummyToken(user_id=303)

    async def fake_get_user_by_id(db, user_id):
        return DummyUser(user_id=user_id, roles=["user"])

    monkeypatch.setattr(crud, "get_api_token_by_raw_token", fake_get_api_token_by_raw_token)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(snippet_utils.get_bearer_auth_or_401(request=request, db=object()))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden"


def test_mcp_http_invalid_jsonrpc_message_returns_400(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers=_base_mcp_headers(),
            content=b'{"id":1}',
        )

    assert response.status_code == 400
    assert "Validation error" in response.text


def test_mcp_http_missing_session_header_returns_400(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers=_base_mcp_headers(),
            json={"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}},
        )

    assert response.status_code == 400
    assert "Missing session ID" in response.text


def test_mcp_http_unknown_session_header_returns_404(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)

    headers = _base_mcp_headers()
    headers[MCP_SESSION_ID_HEADER] = "missing-session-id"
    headers[MCP_PROTOCOL_VERSION_HEADER] = "2025-11-05"

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {}},
        )

    assert response.status_code == 404
    assert "session" in response.text.lower()
