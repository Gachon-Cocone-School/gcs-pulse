from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gcs_pulse.core.session import SessionState

SESSION_FILE = ".gcs-pulse-session.json"


def project_session_path(project_dir: str | Path) -> Path:
    return Path(project_dir).expanduser().resolve() / SESSION_FILE


def new_project(project_dir: str | Path, session: SessionState) -> dict[str, Any]:
    path = project_session_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"project": str(path.parent), "session_file": str(path)}


def save_project(project_dir: str | Path, session: SessionState) -> dict[str, Any]:
    return new_project(project_dir, session)


def load_project(project_dir: str | Path) -> SessionState:
    path = project_session_path(project_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SessionState.from_dict(payload)


def project_status(project_dir: str | Path) -> dict[str, Any]:
    path = project_session_path(project_dir)
    if not path.exists():
        return {"exists": False, "project": str(path.parent), "session_file": str(path)}

    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "exists": True,
        "project": str(path.parent),
        "session_file": str(path),
        "session": payload,
    }
