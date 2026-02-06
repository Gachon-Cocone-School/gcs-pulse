from __future__ import annotations
import time
from typing import Optional, Tuple
import httpx
from app.core.copilot_settings import settings

class TokenManager:
    def __init__(self) -> None:
        creds = settings.load_credentials()
        self.oauth_token: Optional[str] = creds.get("oauth_token")
        self._copilot_token: Optional[str] = creds.get("copilot_token")
        self._copilot_expires_at: Optional[int] = creds.get("copilot_expires_at")
        self._copilot_api_endpoint: Optional[str] = creds.get("copilot_api_endpoint") or None

    def is_copilot_token_valid(self) -> bool:
        if not self._copilot_token or not self._copilot_expires_at:
            return False
        return time.time() < (self._copilot_expires_at - 60)

    def has_oauth_token(self) -> bool:
        return bool(self.oauth_token)

    def get_api_endpoint(self) -> str:
        if self._copilot_api_endpoint:
            return self._copilot_api_endpoint
        # default to GitHub Copilot public URL
        return "https://api.githubcopilot.com"

    async def _request_copilot_token(self, oauth_token: str) -> Tuple[str, int, str]:
        # Mirrors proxy implementation: calls GITHUB_COPILOT_TOKEN_URL with Authorization: token <oauth_token>
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                settings.GITHUB_COPILOT_TOKEN_URL,
                headers={
                    "Authorization": f"token {oauth_token}",
                    "Editor-Version": settings.EDITOR_VERSION,
                    "Editor-Plugin-Version": settings.EDITOR_PLUGIN_VERSION,
                    "Accept": "application/json",
                },
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()

        # proxy returned keys: token, expires_at, endpoints.api
        token = data["token"]
        expires_at = int(data["expires_at"])
        api_endpoint = data.get("endpoints", {}).get("api", settings.GITHUB_COPILOT_API_ENDPOINT) or self.get_api_endpoint()
        return token, expires_at, api_endpoint

    async def get_copilot_token(self) -> str:
        if self.is_copilot_token_valid():
            return self._copilot_token  # type: ignore

        # If we have oauth_token, request a copilot token
        if not self.oauth_token:
            raise ValueError("No OAuth token available to request Copilot token. Provide token via env or credentials JSON.")

        token, expires_at, api_endpoint = await self._request_copilot_token(self.oauth_token)
        self._copilot_token = token
        self._copilot_expires_at = expires_at
        self._copilot_api_endpoint = api_endpoint
        return token

# Single instance (will be created and wired at app startup)
token_manager = TokenManager()
