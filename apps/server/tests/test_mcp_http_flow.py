import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from mcp.server.streamable_http import MCP_SESSION_ID_HEADER

from app.main import app
from app.routers import mcp, snippet_utils


def _base_mcp_headers() -> dict[str, str]:
    return {
        "authorization": "Bearer valid-token",
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
    }


class DummyUser:
    def __init__(self, user_id: int, roles=None):
        self.id = user_id
        self.email = "user@example.com"
        self.name = "User"
        self.roles = roles or ["gcs"]
        self.team_id = None
        self.league_type = "none"


class DummyToken:
    def __init__(self, user_id: int):
        self.user_id = user_id


def _patch_mcp_auth_bypass(monkeypatch) -> None:
    async def fake_get_mcp_user_from_bearer(request, db):
        return mcp.BearerAuthContext(
            user=DummyUser(user_id=1, roles=["gcs"]),
            api_token=DummyToken(user_id=1),
        )

    async def fake_get_snippet_viewer_or_401(request, db):
        _ = (request, db)
        return DummyUser(user_id=1, roles=["gcs"])

    monkeypatch.setattr(mcp, "get_mcp_user_from_bearer", fake_get_mcp_user_from_bearer)
    monkeypatch.setattr(snippet_utils, "get_snippet_viewer_or_401", fake_get_snippet_viewer_or_401)


def _patch_mcp_sample_data(monkeypatch) -> None:
    async def fake_list_daily_snippets(db, viewer, **kwargs):
        return (
            [
                SimpleNamespace(
                    id=11,
                    user_id=viewer.id,
                    date=date(2026, 3, 3),
                    content="daily snippet sample",
                    playbook=None,
                    feedback=None,
                    created_at=datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 3, 3, 11, 0, tzinfo=timezone.utc),
                )
            ],
            1,
        )

    async def fake_list_weekly_snippets(db, viewer, **kwargs):
        return (
            [
                SimpleNamespace(
                    id=21,
                    user_id=viewer.id,
                    week=date(2026, 3, 2),
                    content="weekly snippet sample",
                    playbook=None,
                    feedback=None,
                    created_at=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
                )
            ],
            1,
        )

    async def fake_list_my_achievement_groups(db, user_id):
        return [
            {
                "achievement_definition_id": 100,
                "code": "streak_3",
                "name": "3일 연속",
                "description": "3일 연속 작성",
                "badge_image_url": "https://example.com/badge.png",
                "rarity": "common",
                "grant_count": 1,
                "last_granted_at": datetime(2026, 3, 3, 9, 0, tzinfo=timezone.utc),
            }
        ]

    monkeypatch.setattr(mcp.crud, "list_daily_snippets", fake_list_daily_snippets)
    monkeypatch.setattr(mcp.crud, "list_weekly_snippets", fake_list_weekly_snippets)
    monkeypatch.setattr(mcp.crud, "list_my_achievement_groups", fake_list_my_achievement_groups)


def _extract_sse_json(response_text: str) -> dict:
    for raw_line in response_text.splitlines():
        line = raw_line.strip()
        if line.startswith("data: "):
            return json.loads(line.removeprefix("data: "))
    raise AssertionError("SSE data line not found")


def _initialize_and_get_session_id(client: TestClient) -> str:
    init_response = client.post(
        "/mcp",
        headers=_base_mcp_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1.0"},
            },
        },
    )

    session_id = init_response.headers.get(MCP_SESSION_ID_HEADER)
    assert init_response.status_code == 200
    assert session_id

    initialized_headers = _base_mcp_headers()
    initialized_headers[MCP_SESSION_ID_HEADER] = session_id
    initialized_response = client.post(
        "/mcp",
        headers=initialized_headers,
        json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
    )
    assert initialized_response.status_code in (200, 202)
    return session_id


def test_mcp_http_initialize_returns_session_header(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers=_base_mcp_headers(),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1.0"},
                },
            },
        )

    assert response.status_code == 200
    assert response.headers.get(MCP_SESSION_ID_HEADER)
    payload = _extract_sse_json(response.text)
    assert payload.get("result")


def test_mcp_http_ping_with_session_header_succeeds(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)

    with TestClient(app, base_url="http://localhost") as client:
        session_id = _initialize_and_get_session_id(client)

        ping_headers = _base_mcp_headers()
        ping_headers[MCP_SESSION_ID_HEADER] = session_id

        ping_response = client.post(
            "/mcp",
            headers=ping_headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}},
        )

    assert ping_response.status_code == 200
    payload = _extract_sse_json(ping_response.text)
    assert payload.get("id") == 2


def test_mcp_http_unknown_session_returns_404(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)

    headers = _base_mcp_headers()
    headers[MCP_SESSION_ID_HEADER] = "missing-session"

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {}},
        )

    assert response.status_code == 404
    assert "session" in response.text.lower()


def test_mcp_http_list_tools_exposes_daily_weekly_toolset(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)

    with TestClient(app, base_url="http://localhost") as client:
        session_id = _initialize_and_get_session_id(client)

        list_tools_headers = _base_mcp_headers()
        list_tools_headers[MCP_SESSION_ID_HEADER] = session_id
        response = client.post(
            "/mcp",
            headers=list_tools_headers,
            json={"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}},
        )

    assert response.status_code == 200
    payload = _extract_sse_json(response.text)
    tools = payload["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}

    expected_names = {
        "daily_snippets_page_data",
        "daily_snippets_get",
        "daily_snippets_list",
        "daily_snippets_create",
        "daily_snippets_organize",
        "daily_snippets_feedback",
        "daily_snippets_update",
        "daily_snippets_delete",
        "weekly_snippets_page_data",
        "weekly_snippets_get",
        "weekly_snippets_list",
        "weekly_snippets_create",
        "weekly_snippets_organize",
        "weekly_snippets_feedback",
        "weekly_snippets_update",
        "weekly_snippets_delete",
    }
    assert expected_names.issubset(tool_names)
    assert "get_leaderboard" not in tool_names


def test_mcp_http_call_daily_list_tool_returns_structured_content(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)
    _patch_mcp_sample_data(monkeypatch)

    with TestClient(app, base_url="http://localhost") as client:
        session_id = _initialize_and_get_session_id(client)

        call_headers = _base_mcp_headers()
        call_headers[MCP_SESSION_ID_HEADER] = session_id
        response = client.post(
            "/mcp",
            headers=call_headers,
            json={
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "daily_snippets_list",
                    "arguments": {"limit": 1},
                },
            },
        )

    assert response.status_code == 200
    payload = _extract_sse_json(response.text)
    result = payload["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["total"] == 1
    assert result["structuredContent"]["items"][0]["content"] == "daily snippet sample"


def test_mcp_http_list_and_read_resources(monkeypatch):
    _patch_mcp_auth_bypass(monkeypatch)
    _patch_mcp_sample_data(monkeypatch)

    with TestClient(app, base_url="http://localhost") as client:
        session_id = _initialize_and_get_session_id(client)

        list_headers = _base_mcp_headers()
        list_headers[MCP_SESSION_ID_HEADER] = session_id
        list_response = client.post(
            "/mcp",
            headers=list_headers,
            json={"jsonrpc": "2.0", "id": 12, "method": "resources/list", "params": {}},
        )

        read_headers = _base_mcp_headers()
        read_headers[MCP_SESSION_ID_HEADER] = session_id
        read_response = client.post(
            "/mcp",
            headers=read_headers,
            json={
                "jsonrpc": "2.0",
                "id": 13,
                "method": "resources/read",
                "params": {"uri": "gcs://me/profile"},
            },
        )

    assert list_response.status_code == 200
    list_payload = _extract_sse_json(list_response.text)
    resources = list_payload["result"]["resources"]
    resource_uris = {resource["uri"] for resource in resources}
    assert "gcs://me/profile" in resource_uris
    assert "gcs://me/achievements" in resource_uris
    assert "gcs://achievements/recent" not in resource_uris

    assert read_response.status_code == 200
    read_payload = _extract_sse_json(read_response.text)
    content_text = read_payload["result"]["contents"][0]["text"]
    parsed_content = json.loads(content_text)
    assert parsed_content["id"] == 1
    assert parsed_content["email"] == "user@example.com"


def test_mcp_http_session_owner_mismatch_returns_403(monkeypatch):
    _patch_mcp_sample_data(monkeypatch)

    async def fake_auth_user_1(request, db):
        return mcp.BearerAuthContext(
            user=DummyUser(user_id=1, roles=["gcs"]),
            api_token=DummyToken(user_id=1),
        )

    async def fake_auth_user_2(request, db):
        return mcp.BearerAuthContext(
            user=DummyUser(user_id=2, roles=["gcs"]),
            api_token=DummyToken(user_id=2),
        )

    with TestClient(app, base_url="http://localhost") as client:
        monkeypatch.setattr(mcp, "get_mcp_user_from_bearer", fake_auth_user_1)
        init_response = client.post(
            "/mcp",
            headers=_base_mcp_headers(),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1.0"},
                },
            },
        )
        session_id = init_response.headers[MCP_SESSION_ID_HEADER]

        initialized_headers = _base_mcp_headers()
        initialized_headers[MCP_SESSION_ID_HEADER] = session_id
        client.post(
            "/mcp",
            headers=initialized_headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )

        monkeypatch.setattr(mcp, "get_mcp_user_from_bearer", fake_auth_user_2)
        other_user_headers = _base_mcp_headers()
        other_user_headers[MCP_SESSION_ID_HEADER] = session_id
        response = client.post(
            "/mcp",
            headers=other_user_headers,
            json={"jsonrpc": "2.0", "id": 20, "method": "ping", "params": {}},
        )

    assert response.status_code == 403
    assert "forbidden" in response.text.lower()
