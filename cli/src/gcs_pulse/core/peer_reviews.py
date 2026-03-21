from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def list_sessions(backend: BackendClient) -> dict[str, Any]:
    return backend.get("/peer-reviews/sessions")


def get_session(backend: BackendClient, session_id: int) -> dict[str, Any]:
    return backend.get(f"/peer-reviews/sessions/{session_id}")


def create_session(backend: BackendClient, *, title: str) -> dict[str, Any]:
    return backend.post("/peer-reviews/sessions", body={"title": title})


def update_session(backend: BackendClient, session_id: int, *, title: str) -> dict[str, Any]:
    return backend.patch(f"/peer-reviews/sessions/{session_id}", body={"title": title})


def delete_session(backend: BackendClient, session_id: int) -> dict[str, Any]:
    return backend.delete(f"/peer-reviews/sessions/{session_id}")


def members_confirm(
    backend: BackendClient,
    session_id: int,
    *,
    members: list[dict[str, Any]],
) -> dict[str, Any]:
    """members: [{"student_user_id": int, "team_label": str}, ...]"""
    return backend.post(
        f"/peer-reviews/sessions/{session_id}/members:confirm",
        body={"members": members, "unresolved_members": []},
    )


def status_update(backend: BackendClient, session_id: int, *, is_open: bool) -> dict[str, Any]:
    return backend.patch(
        f"/peer-reviews/sessions/{session_id}/status",
        body={"is_open": is_open},
    )


def get_progress(backend: BackendClient, session_id: int) -> dict[str, Any]:
    return backend.get(f"/peer-reviews/sessions/{session_id}/progress")


def get_results(backend: BackendClient, session_id: int) -> dict[str, Any]:
    return backend.get(f"/peer-reviews/sessions/{session_id}/results")
