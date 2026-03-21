from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def list_sessions(backend: BackendClient) -> dict[str, Any]:
    return backend.get("/tournaments/sessions")


def get_session(backend: BackendClient, session_id: int) -> dict[str, Any]:
    return backend.get(f"/tournaments/sessions/{session_id}")


def create_session(
    backend: BackendClient,
    *,
    title: str,
    allow_self_vote: bool = False,
) -> dict[str, Any]:
    return backend.post(
        "/tournaments/sessions",
        body={"title": title, "allow_self_vote": allow_self_vote},
    )


def update_session(
    backend: BackendClient,
    session_id: int,
    *,
    title: str | None = None,
    allow_self_vote: bool | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if allow_self_vote is not None:
        body["allow_self_vote"] = allow_self_vote
    return backend.patch(f"/tournaments/sessions/{session_id}", body=body)


def delete_session(backend: BackendClient, session_id: int) -> dict[str, Any]:
    return backend.delete(f"/tournaments/sessions/{session_id}")


def members_confirm(
    backend: BackendClient,
    session_id: int,
    *,
    members: list[dict[str, Any]],
) -> dict[str, Any]:
    """members: [{"student_user_id": int, "team_name": str, "can_attend_vote": bool}, ...]"""
    return backend.post(
        f"/tournaments/sessions/{session_id}/members:confirm",
        body={"members": members, "unresolved_members": []},
    )


def format_set(
    backend: BackendClient,
    session_id: int,
    *,
    bracket_size: int,
    repechage: bool = False,
) -> dict[str, Any]:
    return backend.post(
        f"/tournaments/sessions/{session_id}/format:set",
        body={"bracket_size": bracket_size, "repechage": repechage},
    )


def matches_generate(backend: BackendClient, session_id: int) -> dict[str, Any]:
    return backend.post(f"/tournaments/sessions/{session_id}/matches:generate")


def match_progress(backend: BackendClient, match_id: int) -> dict[str, Any]:
    return backend.get(f"/tournaments/matches/{match_id}/progress")


def match_status_update(
    backend: BackendClient,
    match_id: int,
    *,
    status: str,
) -> dict[str, Any]:
    return backend.patch(
        f"/tournaments/matches/{match_id}/status",
        body={"status": status},
    )


def match_votes_reset(backend: BackendClient, match_id: int) -> dict[str, Any]:
    return backend.delete(f"/tournaments/matches/{match_id}/votes")


def match_winner_set(
    backend: BackendClient,
    match_id: int,
    *,
    winner_team_id: int | None,
) -> dict[str, Any]:
    return backend.patch(
        f"/tournaments/matches/{match_id}/winner",
        body={"winner_team_id": winner_team_id},
    )
