"""Registry skill: memilih skill berdasarkan topik percakapan."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.json"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def select_skill(text: str) -> str:
    """Kembalikan nama skill yang paling cocok, atau 'core'."""
    data = load_manifest()
    lowered = text.lower()
    best = "core"
    best_score = 1  # core menang kalau tidak ada keyword cocok

    for name, skill in data.get("skills", {}).items():
        score = 0
        for keyword in skill.get("keywords", []):
            if keyword.lower() in lowered:
                score += 2
        if score > best_score:
            best, best_score = name, score

    return best
