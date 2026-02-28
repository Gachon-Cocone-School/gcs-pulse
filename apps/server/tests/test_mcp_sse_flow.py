import asyncio
import inspect
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request

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


def _decode_event_data(raw_data: str) -> dict:
    return json.loads(raw_data)


def test_mcp_sse_flow_emits_session_and_message_event():
    auth = snippet_utils.BearerAuthContext(user=DummyUser(777), api_token=DummyToken(777))

    async def scenario():
        sse_request = _make_request(
            path="/mcp/sse",
            method="GET",
            headers={"authorization": "Bearer valid-token"},
        )
        sse_response = await inspect.unwrap(mcp.connect_mcp_sse)(
            request=sse_request,
            auth=auth,
        )

        first_event = await asyncio.wait_for(anext(sse_response.body_iterator), timeout=2)
        assert first_event["event"] == "session"

        first_payload = _decode_event_data(first_event["data"])
        session_id = first_payload["session_id"]
        assert isinstance(session_id, str)
        assert session_id

        post_request = _make_request(
            path="/mcp/messages",
            method="POST",
            headers={
                "authorization": "Bearer valid-token",
                "content-type": "application/json",
            },
            body=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
        )

        post_response = await inspect.unwrap(mcp.post_mcp_message)(
            request=post_request,
            session_id=session_id,
            auth=auth,
        )
        assert post_response["ok"] is True
        assert post_response["session_id"] == session_id

        second_event = await asyncio.wait_for(anext(sse_response.body_iterator), timeout=2)
        assert second_event["event"] == "message"

        second_payload = _decode_event_data(second_event["data"])
        assert second_payload["session_id"] == session_id
        assert second_payload["message"]["method"] == "initialize"

        await mcp.registry.remove(session_id)

    asyncio.run(scenario())


def test_mcp_sse_flow_unknown_session_returns_404():
    auth = snippet_utils.BearerAuthContext(user=DummyUser(888), api_token=DummyToken(888))

    async def scenario():
        post_request = _make_request(
            path="/mcp/messages",
            method="POST",
            headers={
                "authorization": "Bearer valid-token",
                "content-type": "application/json",
            },
            body=b'{"jsonrpc":"2.0","id":2,"method":"ping"}',
        )
        await inspect.unwrap(mcp.post_mcp_message)(
            request=post_request,
            session_id="missing-session-id",
            auth=auth,
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(scenario())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "MCP session not found"
