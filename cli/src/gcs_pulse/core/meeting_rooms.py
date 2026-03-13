from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def list_rooms(backend: BackendClient) -> dict[str, Any]:
    return backend.get("/meeting-rooms")


def list_reservations(backend: BackendClient, *, room_id: int, date: str) -> dict[str, Any]:
    return backend.get(f"/meeting-rooms/{room_id}/reservations", query={"date": date})


def create_reservation(
    backend: BackendClient,
    *,
    room_id: int,
    start_at: str,
    end_at: str,
    purpose: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "start_at": start_at,
        "end_at": end_at,
    }
    if purpose is not None:
        payload["purpose"] = purpose
    return backend.post(f"/meeting-rooms/{room_id}/reservations", body=payload)


def cancel_reservation(backend: BackendClient, *, reservation_id: int) -> dict[str, Any]:
    return backend.delete(f"/meeting-rooms/reservations/{reservation_id}")
