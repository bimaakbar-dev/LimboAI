"""Buat dataset khusus skill 'asisten-ringan' dari dataset utama."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "training" / "dataset.jsonl"
MANIFEST = ROOT / "skills" / "manifest.json"
TARGET = ROOT / "skills" / "asisten-ringan" / "dataset.jsonl"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    keywords = [
        keyword.lower()
        for skill in manifest.get("skills", {}).values()
        for keyword in skill.get("keywords", [])
    ]

    rows = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        user_text = " ".join(
            message["content"]
            for message in record["messages"]
            if message["role"] == "user"
        ).lower()
        if any(keyword in user_text for keyword in keywords):
            rows.append(record)

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with TARGET.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Dataset skill ditulis: {TARGET}")
    print(f"Jumlah contoh: {len(rows)}")


if __name__ == "__main__":
    main()
