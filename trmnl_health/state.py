from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

STATE_DIR = Path.home() / ".cache" / "trmnl_health"
STATE_FILE = STATE_DIR / "state.json"


def load_last_hash() -> Optional[str]:
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:  # pragma: no cover - defensive
        return None
    return data.get("last_payload_hash")


def save_last_hash(payload_hash: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_payload_hash": payload_hash}, indent=2))
