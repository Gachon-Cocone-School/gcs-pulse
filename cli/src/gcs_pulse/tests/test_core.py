from __future__ import annotations

import json
from pathlib import Path

import pytest

from gcs_pulse.core.project import load_project, new_project, project_status, save_project
from gcs_pulse.core.session import SessionState
from gcs_pulse.gcs_pulse_cli import _resolve_cli
from gcs_pulse.utils.gcs_pulse_backend import BackendClient, BackendError
from gcs_pulse.utils.output import error_payload, success_payload


def test_session_roundtrip() -> None:
    state = SessionState(
        server_url="http://localhost:8000",
        api_token="abc",
        timeout=12.5,
        project="/tmp/p",
        context={"k": "v"},
    )
    loaded = SessionState.from_dict(state.to_dict())
    assert loaded.server_url == "http://localhost:8000"
    assert loaded.api_token == "abc"
    assert loaded.timeout == 12.5
    assert loaded.project == "/tmp/p"
    assert loaded.context == {"k": "v"}


def test_project_new_save_load_status(tmp_path: Path) -> None:
    state = SessionState(server_url="http://localhost:8000", api_token="t", timeout=20.0)

    created = new_project(tmp_path, state)
    assert Path(created["session_file"]).exists()

    saved = save_project(tmp_path, state)
    assert created["session_file"] == saved["session_file"]

    status = project_status(tmp_path)
    assert status["exists"] is True
    assert status["session"]["server_url"] == "http://localhost:8000"

    loaded = load_project(tmp_path)
    assert loaded.api_token == "t"


def test_project_status_not_exists(tmp_path: Path) -> None:
    status = project_status(tmp_path)
    assert status["exists"] is False


def test_output_success_error_payload() -> None:
    ok = success_payload("auth status", {"a": 1})
    assert ok["ok"] is True
    assert ok["command"] == "auth status"
    assert ok["data"] == {"a": 1}

    err = error_payload("X", "failed", {"reason": "boom"})
    assert err["ok"] is False
    assert err["error"]["code"] == "X"


def test_resolve_cli_prefers_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/gcs-pulse-cli")
    resolved = _resolve_cli("gcs-pulse-cli")
    assert resolved == ["/usr/local/bin/gcs-pulse-cli"]


def test_resolve_cli_module_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.delenv("CLI_ANYTHING_FORCE_INSTALLED", raising=False)
    resolved = _resolve_cli("gcs-pulse-cli")
    assert resolved[1:] == ["-m", "gcs_pulse"]


def test_resolve_cli_force_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setenv("CLI_ANYTHING_FORCE_INSTALLED", "1")
    with pytest.raises(RuntimeError):
        _resolve_cli("gcs-pulse-cli")


def test_backend_build_url_and_query() -> None:
    backend = BackendClient(server_url="http://localhost:8000/", api_token="x")
    url = backend._build_url("/daily-snippets", {"limit": 5, "q": "abc", "skip": None})
    assert url.startswith("http://localhost:8000/daily-snippets?")
    assert "limit=5" in url
    assert "q=abc" in url
    assert "skip=" not in url


def test_backend_script_missing() -> None:
    backend = BackendClient(server_url="http://localhost:8000", api_token="x")
    with pytest.raises(BackendError) as exc:
        backend.run_script("__definitely_missing_script__.py")
    assert exc.value.code == "MISSING_DEPENDENCY"


def test_session_file_json_shape(tmp_path: Path) -> None:
    state = SessionState(server_url="http://localhost:8000", api_token="z", timeout=9.0)
    new_project(tmp_path, state)
    session_file = tmp_path / ".gcs-pulse-session.json"
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert sorted(payload.keys()) == ["api_token", "context", "project", "server_url", "timeout"]
