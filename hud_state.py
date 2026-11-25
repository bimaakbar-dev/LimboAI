"""Jembatan status asisten -> HUD avatar.

Asisten menulis state ke hud_state.json; HUD membacanya lewat /api/state.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "hud_state.json"

DEFAULT = {"state": "idle", "route": "idle", "updated": 0}


def set_state(state: str, route: str | None = None) -> None:
    payload = {
        "state": state,
        "route": route or state,
        "updated": time.time(),
    }
    try:
        STATE_FILE.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def get_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(DEFAULT)
