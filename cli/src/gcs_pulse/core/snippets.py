from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def _list(backend: BackendClient, kind: str, **query: Any) -> dict[str, Any]:
    path = f"/{kind}-snippets"
    return backend.get(path, query=query)


def _get(backend: BackendClient, kind: str, snippet_id: int) -> dict[str, Any]:
    return backend.get(f"/{kind}-snippets/{snippet_id}")


def _create(backend: BackendClient, kind: str, content: str) -> dict[str, Any]:
    return backend.post(f"/{kind}-snippets", body={"content": content})


def _organize(backend: BackendClient, kind: str, content: str) -> dict[str, Any]:
    return backend.post(f"/{kind}-snippets/organize", body={"content": content})


def _feedback(backend: BackendClient, kind: str) -> dict[str, Any]:
    return backend.get(f"/{kind}-snippets/feedback")


def _update(backend: BackendClient, kind: str, snippet_id: int, content: str) -> dict[str, Any]:
    return backend.put(f"/{kind}-snippets/{snippet_id}", body={"content": content})


def _delete(backend: BackendClient, kind: str, snippet_id: int) -> dict[str, Any]:
    return backend.delete(f"/{kind}-snippets/{snippet_id}")


def daily_list(backend: BackendClient, **query: Any) -> dict[str, Any]:
    return _list(backend, "daily", **query)


def daily_get(backend: BackendClient, snippet_id: int) -> dict[str, Any]:
    return _get(backend, "daily", snippet_id)


def daily_create(backend: BackendClient, content: str) -> dict[str, Any]:
    return _create(backend, "daily", content)


def daily_organize(backend: BackendClient, content: str) -> dict[str, Any]:
    return _organize(backend, "daily", content)


def daily_feedback(backend: BackendClient) -> dict[str, Any]:
    return _feedback(backend, "daily")


def daily_update(backend: BackendClient, snippet_id: int, content: str) -> dict[str, Any]:
    return _update(backend, "daily", snippet_id, content)


def daily_delete(backend: BackendClient, snippet_id: int) -> dict[str, Any]:
    return _delete(backend, "daily", snippet_id)


def weekly_list(backend: BackendClient, **query: Any) -> dict[str, Any]:
    return _list(backend, "weekly", **query)


def weekly_get(backend: BackendClient, snippet_id: int) -> dict[str, Any]:
    return _get(backend, "weekly", snippet_id)


def weekly_create(backend: BackendClient, content: str) -> dict[str, Any]:
    return _create(backend, "weekly", content)


def weekly_organize(backend: BackendClient, content: str) -> dict[str, Any]:
    return _organize(backend, "weekly", content)


def weekly_feedback(backend: BackendClient) -> dict[str, Any]:
    return _feedback(backend, "weekly")


def weekly_update(backend: BackendClient, snippet_id: int, content: str) -> dict[str, Any]:
    return _update(backend, "weekly", snippet_id, content)


def weekly_delete(backend: BackendClient, snippet_id: int) -> dict[str, Any]:
    return _delete(backend, "weekly", snippet_id)
