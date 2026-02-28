import asyncio
import inspect

import pytest
from fastapi import HTTPException
from fastapi.params import Depends as DependsParam
from starlette.requests import Request

from app import crud
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


def test_mcp_routes_require_same_bearer_dependency():
    for endpoint in (mcp.connect_mcp_sse, mcp.post_mcp_message):
        signature = inspect.signature(inspect.unwrap(endpoint))
        auth_default = signature.parameters["auth"].default
        assert isinstance(auth_default, DependsParam)
        assert auth_default.dependency is mcp.get_mcp_user_from_bearer


def test_bearer_auth_missing_token_returns_401():
    request = _make_request(path="/mcp/sse", method="GET")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(snippet_utils.get_bearer_auth_or_401(request=request, db=object()))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API token"


def test_bearer_auth_invalid_token_returns_401(monkeypatch):
    request = _make_request(
        path="/mcp/sse",
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
        path="/mcp/sse",
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
        path="/mcp/sse",
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


def test_bearer_auth_invalid_jsonrpc_message_returns_400():
    auth = snippet_utils.BearerAuthContext(user=DummyUser(301), api_token=DummyToken(301))

    async def scenario():
        session = await mcp.registry.create(user_id=auth.user.id)
        request = _make_request(
            path="/mcp/messages",
            method="POST",
            headers={"content-type": "application/json"},
            body=b'{"id":1}',
        )
        try:
            await inspect.unwrap(mcp.post_mcp_message)(
                request=request,
                session_id=session.session_id,
                auth=auth,
            )
        finally:
            await mcp.registry.remove(session.session_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(scenario())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid MCP message"


def test_mcp_messages_other_user_session_returns_403():
    owner_auth = snippet_utils.BearerAuthContext(user=DummyUser(201), api_token=DummyToken(201))
    other_auth = snippet_utils.BearerAuthContext(user=DummyUser(202), api_token=DummyToken(202))

    async def scenario():
        session = await mcp.registry.create(user_id=owner_auth.user.id)
        request = _make_request(
            path="/mcp/messages",
            method="POST",
            headers={"content-type": "application/json"},
            body=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
        )
        try:
            await inspect.unwrap(mcp.post_mcp_message)(
                request=request,
                session_id=session.session_id,
                auth=other_auth,
            )
        finally:
            await mcp.registry.remove(session.session_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(scenario())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "MCP session forbidden"
