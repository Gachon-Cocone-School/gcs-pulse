from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MCP_SESSION_ID_HEADER = "mcp-session-id"


class BackendError(RuntimeError):
    def __init__(self, code: str, message: str, details: Any = None, *, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.status = status


@dataclass
class BackendClient:
    server_url: str
    api_token: str
    timeout: float = 20.0
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.server_url = self.server_url.rstrip("/")

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[4]

    @property
    def server_root(self) -> Path:
        return self.repo_root / "apps" / "server"

    @property
    def scripts_root(self) -> Path:
        return self.server_root / "scripts"

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        url = f"{self.server_url}{path}"
        if query:
            compact = {k: v for k, v in query.items() if v is not None and v != ""}
            if compact:
                url = f"{url}?{urlencode(compact)}"
        return url

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> dict[str, Any]:
        body_bytes = None
        request_headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        if require_auth:
            if not self.api_token:
                raise BackendError("AUTH_REQUIRED", "api-token is required")
            request_headers["authorization"] = f"Bearer {self.api_token}"

        if headers:
            request_headers.update(headers)

        if json_body is not None:
            body_bytes = json.dumps(json_body).encode("utf-8")

        req = Request(
            self._build_url(path, query=query),
            method=method.upper(),
            headers=request_headers,
            data=body_bytes,
        )

        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else {}
                result = parsed if isinstance(parsed, dict) else {"value": parsed}
                if MCP_SESSION_ID_HEADER in response.headers:
                    self.context["mcp_session_id"] = response.headers[MCP_SESSION_ID_HEADER]
                return result
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            parsed: Any
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"raw": raw}
            message = "HTTP request failed"
            details = parsed
            if isinstance(parsed, dict):
                message = str(parsed.get("detail") or parsed.get("message") or message)
            raise BackendError(
                code="HTTP_ERROR",
                message=message,
                details=details,
                status=exc.code,
            ) from exc
        except URLError as exc:
            raise BackendError(
                code="CONNECTION_ERROR",
                message="Failed to connect to server",
                details=str(exc.reason),
            ) from exc

    def get(self, path: str, *, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path, query=query)

    def post(self, path: str, *, body: dict[str, Any] | None = None, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", path, json_body=body, query=query)

    def put(self, path: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("PUT", path, json_body=body)

    def delete(self, path: str) -> dict[str, Any]:
        return self._request("DELETE", path)

    def mcp_initialize(self) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "gcs-pulse-cli", "version": "0.1.0"},
            },
        }
        result = self._mcp_request(payload)
        self._mcp_notify_initialized()
        return result

    def _mcp_notify_initialized(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        self._mcp_request(payload, expect_result=False)

    def _mcp_request(self, payload: dict[str, Any], *, expect_result: bool = True) -> dict[str, Any]:
        headers: dict[str, str] = {}
        session_id = self.context.get("mcp_session_id")
        if session_id:
            headers[MCP_SESSION_ID_HEADER] = str(session_id)

        response = self._request("POST", "/mcp", json_body=payload, headers=headers)
        if not expect_result:
            return response

        if "error" in response:
            error = response["error"]
            raise BackendError(
                code="MCP_ERROR",
                message=str(error.get("message") or "MCP call failed"),
                details=error,
            )
        return response.get("result", response)

    def mcp_tools_list(self) -> dict[str, Any]:
        if not self.context.get("mcp_session_id"):
            self.mcp_initialize()
        return self._mcp_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    def mcp_resources_list(self) -> dict[str, Any]:
        if not self.context.get("mcp_session_id"):
            self.mcp_initialize()
        return self._mcp_request({"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}})

    def mcp_resources_read(self, uri: str) -> dict[str, Any]:
        if not self.context.get("mcp_session_id"):
            self.mcp_initialize()
        return self._mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "resources/read",
                "params": {"uri": uri},
            }
        )

    def mcp_tools_call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.context.get("mcp_session_id"):
            self.mcp_initialize()
        return self._mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )

    def run_script(self, script_name: str, args: list[str] | None = None) -> dict[str, Any]:
        script_path = self.scripts_root / script_name
        if not script_path.exists():
            raise BackendError(
                code="MISSING_DEPENDENCY",
                message=f"Required script not found: {script_path}",
                details={
                    "hint": "gcs-pulse/apps/server/scripts 를 확인하고 의존성을 설치한 뒤 다시 실행하세요.",
                },
            )

        command = [sys.executable, str(script_path), *(args or [])]
        env = os.environ.copy()

        try:
            proc = subprocess.run(
                command,
                cwd=str(self.server_root),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise BackendError(
                code="MISSING_DEPENDENCY",
                message="Python runtime not found",
                details=str(exc),
            ) from exc

        result = {
            "command": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
        if proc.returncode != 0:
            raise BackendError(
                code="SCRIPT_FAILED",
                message=f"Script failed: {script_name}",
                details=result,
            )
        return result
