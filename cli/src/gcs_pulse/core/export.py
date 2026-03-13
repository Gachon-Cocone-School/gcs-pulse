from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_json(path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(target), "bytes": target.stat().st_size}
