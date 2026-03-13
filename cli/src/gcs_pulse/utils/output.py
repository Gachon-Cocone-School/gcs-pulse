from __future__ import annotations

import json
from typing import Any


def success_payload(command: str, data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "data": data,
        "meta": meta or {},
    }


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }


def emit(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False))
        return

    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
