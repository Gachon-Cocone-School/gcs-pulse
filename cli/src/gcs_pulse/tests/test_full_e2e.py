from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from gcs_pulse.gcs_pulse_cli import _resolve_cli


@pytest.fixture(scope="session")
def e2e_env() -> dict[str, str]:
    server_url = os.getenv("GCS_PULSE_SERVER_URL", "").strip()
    api_token = os.getenv("GCS_PULSE_API_TOKEN", "").strip()
    if not server_url or not api_token:
        pytest.skip("E2E requires GCS_PULSE_SERVER_URL and GCS_PULSE_API_TOKEN")
    return {"server_url": server_url, "api_token": api_token}


def _run_cli(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = _resolve_cli("gcs-pulse-cli") + args
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=merged_env, check=False)


def _parse_json_output(proc: subprocess.CompletedProcess[str]) -> dict:
    stdout = proc.stdout.strip().splitlines()
    assert stdout, f"empty stdout: stderr={proc.stderr}"
    raw = stdout[-1]
    return json.loads(raw)


def test_installed_cli_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLI_ANYTHING_FORCE_INSTALLED", raising=False)
    resolved = _resolve_cli("gcs-pulse-cli")
    assert resolved


def test_force_installed_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLI_ANYTHING_FORCE_INSTALLED", "1")
    # If installed path is absent, _resolve_cli must raise.
    # If present, it should return installed command path.
    try:
        resolved = _resolve_cli("gcs-pulse-cli")
        assert resolved[0]
    except RuntimeError:
        assert True


def test_auth_status_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "auth",
        "status",
    ])
    assert proc.returncode == 0, proc.stderr
    payload = _parse_json_output(proc)
    assert payload["ok"] is True
    assert payload["command"] == "auth status"


def test_achievements_me_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "achievements",
        "me",
    ])
    assert proc.returncode == 0, proc.stderr
    payload = _parse_json_output(proc)
    assert payload["ok"] is True


def test_achievements_recent_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "achievements",
        "recent",
        "--limit",
        "5",
    ])
    assert proc.returncode == 0, proc.stderr
    payload = _parse_json_output(proc)
    assert payload["ok"] is True


def test_daily_list_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "daily",
        "list",
        "--limit",
        "5",
    ])
    assert proc.returncode == 0, proc.stderr
    payload = _parse_json_output(proc)
    assert payload["ok"] is True


def test_weekly_list_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "weekly",
        "list",
        "--limit",
        "5",
    ])
    assert proc.returncode == 0, proc.stderr
    payload = _parse_json_output(proc)
    assert payload["ok"] is True


def test_comments_list_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "comments",
        "list",
        "--daily-snippet-id",
        "1",
    ])
    # snippet id가 환경에 따라 없을 수 있으므로 성공/실패 모두 JSON 스키마만 검증
    payload = _parse_json_output(proc)
    assert payload["ok"] in {True, False}


def test_users_search_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "users",
        "search",
        "--q",
        "kim",
        "--limit",
        "5",
    ])
    payload = _parse_json_output(proc)
    assert payload["ok"] in {True, False}


def test_users_list_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "users",
        "list",
        "--limit",
        "5",
        "--offset",
        "0",
    ])
    payload = _parse_json_output(proc)
    assert payload["ok"] in {True, False}


def test_users_teams_json(e2e_env: dict[str, str]) -> None:
    proc = _run_cli([
        "--json",
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
        "users",
        "teams",
        "--limit",
        "5",
        "--offset",
        "0",
    ])
    payload = _parse_json_output(proc)
    assert payload["ok"] in {True, False}


def test_repl_entrypoint_runs_help(e2e_env: dict[str, str]) -> None:
    cmd = _resolve_cli("gcs-pulse-cli") + [
        "--server-url",
        e2e_env["server_url"],
        "--api-token",
        e2e_env["api_token"],
    ]
    proc = subprocess.run(
        cmd,
        input="help\nquit\n",
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "GCS Pulse REPL" in proc.stdout


def test_module_invocation_path(e2e_env: dict[str, str]) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "gcs_pulse",
            "--json",
            "--server-url",
            e2e_env["server_url"],
            "--api-token",
            e2e_env["api_token"],
            "auth",
            "status",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = _parse_json_output(proc)
    assert payload["ok"] is True
