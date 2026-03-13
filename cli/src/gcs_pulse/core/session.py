from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    server_url: str
    api_token: str
    timeout: float = 20.0
    project: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_url": self.server_url,
            "api_token": self.api_token,
            "timeout": self.timeout,
            "project": self.project,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionState":
        return cls(
            server_url=str(payload.get("server_url") or ""),
            api_token=str(payload.get("api_token") or ""),
            timeout=float(payload.get("timeout") or 20.0),
            project=payload.get("project"),
            context=dict(payload.get("context") or {}),
        )
