from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def list_tools(backend: BackendClient) -> dict[str, Any]:
    return backend.mcp_tools_list()


def list_resources(backend: BackendClient) -> dict[str, Any]:
    return backend.mcp_resources_list()


def read_resource(backend: BackendClient, uri: str) -> dict[str, Any]:
    return backend.mcp_resources_read(uri)


def call_tool(backend: BackendClient, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return backend.mcp_tools_call(tool_name, arguments)
