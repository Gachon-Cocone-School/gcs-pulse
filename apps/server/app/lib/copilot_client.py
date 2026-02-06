from __future__ import annotations
from typing import Optional, Any, Dict
import asyncio
import httpx
from app.core.copilot_settings import settings
from app.lib.copilot_token_manager import token_manager

class CopilotClient:
    def __init__(self, timeout: Optional[int] = None) -> None:
        self._timeout = timeout or settings.COPILOT_REQUEST_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
        # Optional lock to serialize token refresh to avoid thundering herd
        self._token_lock = asyncio.Lock()

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)

    def _build_headers(self, copilot_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {copilot_token}",
            "Content-Type": "application/json",
            "Editor-Version": settings.EDITOR_VERSION,
            "Editor-Plugin-Version": settings.EDITOR_PLUGIN_VERSION,
            "Openai-Intent": "conversation-panel",
            "Openai-Organization": "github-copilot",
            "User-Agent": "GitHubCopilotChat/0.12.0",
            "Accept": "application/json",
        }

    async def request(self, method: str, path: str, *, json: Optional[dict] = None, params: Optional[dict] = None) -> Any:
        await self._ensure_client()

        # Acquire token (serialize refresh)
        async with self._token_lock:
            copilot_token = await token_manager.get_copilot_token()
            api_endpoint = token_manager.get_api_endpoint()

        url = path if path.startswith("http") else f"{api_endpoint.rstrip('/')}/{path.lstrip('/')}"
        headers = self._build_headers(copilot_token)

        # Simple retry for 429/5xx
        retries = 3
        backoff = 0.5
        last_exc = None
        for attempt in range(retries):
            try:
                resp = await self._client.request(method, url, json=json, params=params, headers=headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 401:
                    # token likely invalid -> force refresh and retry once
                    # clear stored token and retry
                    token_manager._copilot_token = None  # intentionally simple
                    if attempt == retries - 1:
                        raise
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                if status in (429, 502, 503, 504):
                    last_exc = e
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise
            except httpx.RequestError as e:
                last_exc = e
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

        # If reached here, raise last exception
        if last_exc:
            raise last_exc
        raise RuntimeError("Unknown error while calling Copilot API")

    async def chat(
        self,
        messages: list[dict],
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> dict:
        payload = {
            "messages": messages,
            "model": model or settings.COPILOT_DEFAULT_MODEL,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Merge extra arguments (like response_format) into payload
        payload.update(kwargs)

        return await self.request("POST", "/chat/completions", json=payload)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

# We'll create the instance at startup and expose via app.state or a dependency
copilot_client: Optional[CopilotClient] = None
