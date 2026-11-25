"""Download model lokal Qwen2.5-3B-Instruct Q4_K_M (GGUF).

Pakai:
    python download_model.py

Alternatif manual: unduh file ke folder models/ lalu ubah 'model_label' di config.json.
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

DEFAULT_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/"
    "qwen2.5-3b-instruct-q4_k_m.gguf"
)
DESTINATION = Path(__file__).resolve().parent / "models" / "qwen2.5-3b-instruct-q4_k_m.gguf"


def main() -> None:
    url = os.environ.get("MODEL_URL", DEFAULT_URL)
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.exists():
        print(f"File sudah ada: {DESTINATION}")
        return

    print(f"Mengunduh:\n{url}\nke {DESTINATION}")
    print("Ini bisa memakan waktu beberapa menit (file sekitar 2 GB).")

    def progress(count: int, block: int, total: int) -> None:
        if total <= 0:
            return
        percent = min(100, int(count * block * 100 / total))
        print(f"\r{percent:3d}%", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, str(DESTINATION), reporthook=progress)
    except Exception as exc:
        print(f"\nGagal mengunduh: {exc}")
        print("Cek nama file di https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/tree/main")
        print("Lalu set environment MODEL_URL ke URL file .gguf yang tersedia.")
        sys.exit(1)
    print(f"\nSelesai: {DESTINATION} ({DESTINATION.stat().st_size / (1024**3):.2f} GB)")


if __name__ == "__main__":
    main()
