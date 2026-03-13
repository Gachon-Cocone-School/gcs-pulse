from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def my_achievements(backend: BackendClient) -> dict[str, Any]:
    return backend.get("/achievements/me")


def recent_achievements(backend: BackendClient, *, limit: int = 10) -> dict[str, Any]:
    return backend.get("/achievements/recent", query={"limit": limit})
