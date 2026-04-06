from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def search_students(backend: BackendClient, *, q: str, limit: int = 20) -> dict[str, Any]:
    return backend.get("/users/students/search", query={"q": q, "limit": limit})


def list_students(backend: BackendClient, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return backend.get("/users/students", query={"limit": limit, "offset": offset})


def list_teams(backend: BackendClient, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return backend.get("/teams", query={"limit": limit, "offset": offset})


def get_token_usage(backend: BackendClient) -> dict[str, Any]:
    return backend.get("/users/me/token-usage")
