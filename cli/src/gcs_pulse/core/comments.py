from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def list_comments(
    backend: BackendClient,
    *,
    daily_snippet_id: int | None = None,
    weekly_snippet_id: int | None = None,
) -> dict[str, Any]:
    query = {
        "daily_snippet_id": daily_snippet_id,
        "weekly_snippet_id": weekly_snippet_id,
    }
    return backend.get("/comments", query=query)


def create_comment(
    backend: BackendClient,
    *,
    content: str,
    comment_type: str,
    daily_snippet_id: int | None = None,
    weekly_snippet_id: int | None = None,
) -> dict[str, Any]:
    body = {
        "content": content,
        "comment_type": comment_type,
        "daily_snippet_id": daily_snippet_id,
        "weekly_snippet_id": weekly_snippet_id,
    }
    return backend.post("/comments", body=body)


def update_comment(backend: BackendClient, comment_id: int, *, content: str) -> dict[str, Any]:
    return backend.put(f"/comments/{comment_id}", body={"content": content})


def delete_comment(backend: BackendClient, comment_id: int) -> dict[str, Any]:
    return backend.delete(f"/comments/{comment_id}")
