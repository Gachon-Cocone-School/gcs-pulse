from __future__ import annotations
from typing import Optional
import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class CopilotSettings(BaseSettings):
    # Accept either a JSON blob or separate env vars.
    GITHUB_COPILOT_CREDENTIALS_JSON: Optional[str] = None

    # Optional standalone env vars (if not using JSON)
    GITHUB_OAUTH_TOKEN: Optional[str] = None
    GITHUB_COPILOT_COOKIE: Optional[str] = None  # copilot_token cookie-like string
    GITHUB_COPILOT_EXPIRES_AT: Optional[int] = None
    GITHUB_COPILOT_API_ENDPOINT: Optional[str] = None

    # Copilot token request endpoint (used when we have oauth token and must request copilot token)
    GITHUB_COPILOT_TOKEN_URL: str = "https://api.github.com/copilot_internal/v2/token"

    # Editor headers used by upstream proxy code; keep defaults from proxy for compatibility
    EDITOR_VERSION: str = "vscode/1.85.0"
    EDITOR_PLUGIN_VERSION: str = "copilot/1.143.0"

    # client defaults
    COPILOT_DEFAULT_MODEL: str = "gpt-5-mini"
    COPILOT_REQUEST_TIMEOUT: int = 60

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def load_credentials(self) -> dict:
        """
        Return a dict with keys:
        - oauth_token
        - copilot_token
        - copilot_expires_at
        - copilot_api_endpoint
        Values may be None if not provided.
        """
        if self.GITHUB_COPILOT_CREDENTIALS_JSON:
            try:
                data = json.loads(self.GITHUB_COPILOT_CREDENTIALS_JSON)
                return {
                    "oauth_token": data.get("oauth_token"),
                    "copilot_token": data.get("copilot_token"),
                    "copilot_expires_at": data.get("copilot_expires_at"),
                    "copilot_api_endpoint": data.get("copilot_api_endpoint"),
                }
            except Exception:
                # invalid JSON — fall through to individual vars
                pass

        return {
            "oauth_token": self.GITHUB_OAUTH_TOKEN,
            "copilot_token": self.GITHUB_COPILOT_COOKIE,
            "copilot_expires_at": self.GITHUB_COPILOT_EXPIRES_AT,
            "copilot_api_endpoint": str(self.GITHUB_COPILOT_API_ENDPOINT) if self.GITHUB_COPILOT_API_ENDPOINT else None,
        }


settings = CopilotSettings()
