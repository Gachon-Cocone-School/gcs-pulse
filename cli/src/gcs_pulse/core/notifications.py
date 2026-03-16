from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def list_notifications(
    backend: BackendClient,
    *,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    return backend.get("/notifications", query={"limit": limit, "offset": offset})


def unread_count(backend: BackendClient) -> dict[str, Any]:
    return backend.get("/notifications/unread-count")


def mark_as_read(backend: BackendClient, notification_id: int) -> dict[str, Any]:
    return backend.patch(f"/notifications/{notification_id}/read")


def mark_all_as_read(backend: BackendClient) -> dict[str, Any]:
    return backend.patch("/notifications/read-all")


def get_settings(backend: BackendClient) -> dict[str, Any]:
    return backend.get("/notifications/settings")


def update_settings(
    backend: BackendClient,
    *,
    notify_post_author: bool | None = None,
    notify_mentions: bool | None = None,
    notify_participants: bool | None = None,
) -> dict[str, Any]:
    body = {}
    if notify_post_author is not None:
        body["notify_post_author"] = notify_post_author
    if notify_mentions is not None:
        body["notify_mentions"] = notify_mentions
    if notify_participants is not None:
        body["notify_participants"] = notify_participants
    return backend.patch("/notifications/settings", body=body)
