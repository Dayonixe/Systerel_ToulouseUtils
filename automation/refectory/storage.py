from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any


def read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback

    if not isinstance(payload, dict):
        raise ValueError(f"Le fichier {path.name} doit contenir un objet JSON")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON safely, including while Vite watches the target on Windows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(serialised, encoding="utf-8")

    for delay in (0.02, 0.05, 0.1, 0.2, 0.4):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            time.sleep(delay)

    # Vite can keep the destination open without delete sharing on Windows.
    path.write_text(serialised, encoding="utf-8")
    temporary.unlink(missing_ok=True)
