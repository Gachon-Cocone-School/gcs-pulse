import pytest
import respx
import httpx
from app.lib.copilot_client import CopilotClient
from app.lib.copilot_token_manager import token_manager
from app.core.copilot_settings import settings

@pytest.mark.asyncio
async def test_chat_success():
    tm = token_manager
    tm.oauth_token = "fake-oauth-token"

    with respx.mock:
        respx.get(settings.GITHUB_COPILOT_TOKEN_URL).respond(200, json={
            "token": "copilot-token-xyz",
            "expires_at": int(9999999999),
            "endpoints": {"api": "https://api.individual.githubcopilot.com"}
        })

        respx.post("https://api.individual.githubcopilot.com/chat/completions").respond(200, json={
            "choices": [{"message": {"content": "hello from copilot"}}]
        })

        client = CopilotClient(timeout=10)
        resp = await client.chat([{"role": "user", "content": "hi"}])
        assert isinstance(resp, dict)
        assert "choices" in resp or "reply" in resp
        await client.close()

@pytest.mark.asyncio
async def test_401_refresh():
    tm = token_manager
    tm.oauth_token = "fake-oauth-token-2"
    tm._copilot_token = None

    with respx.mock:
        respx.get(settings.GITHUB_COPILOT_TOKEN_URL).respond(200, json={
            "token": "new-token",
            "expires_at": int(9999999999),
            "endpoints": {"api": "https://api.individual.githubcopilot.com"}
        })

        mock_route = respx.post("https://api.individual.githubcopilot.com/chat/completions")
        mock_route.side_effect = [
            httpx.Response(401, json={"message": "unauth"}),
            httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        ]

        client = CopilotClient(timeout=10)
        resp = await client.chat([{"role": "user", "content": "hi again"}])
        assert isinstance(resp, dict)
        await client.close()
