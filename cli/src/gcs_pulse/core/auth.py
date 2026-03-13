from __future__ import annotations

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def auth_status(backend: BackendClient) -> dict:
    return backend.get("/auth/me")


def auth_verify(backend: BackendClient) -> dict:
    me = backend.get("/auth/me")
    profile = backend.mcp_resources_read("gcs://me/profile")
    return {
        "auth": me,
        "mcp_profile": profile,
    }
