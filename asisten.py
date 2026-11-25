"""Entry point Asisten PC v1.

Pemakaian:
    python asisten.py                      # mode interaktif
    python asisten.py "cek spec pc"        # sekali jalan
    python asisten.py /status              # perintah khusus
"""
from __future__ import annotations

import sys
from pathlib import Path

from core.assistant import Assistant

ROOT = Path(__file__).resolve().parent

HELP = """Perintah khusus:
  /spec              tampilkan spesifikasi PC
  /status            status otak lokal, Gemini API, area kerja
  /mode auto         pakai lokal dulu, cloud kalau perlu (default)
  /mode local        paksa otak lokal
  /mode cloud        paksa Gemini API
  /help              tampilkan bantuan ini
  exit / keluar      keluar

Contoh:
  cek spec pc
  lihat isi folder workspace
  cek ruang disk
  cari duplikat di folder workspace
  proses dengan CPU tertinggi
  apakah internet tersedia?

Ketik 'konfirmasi' setelah asisten meminta izin untuk aksi destruktif.
"""


def run_command(assistant: Assistant, raw: str) -> bool:
    parts = raw.strip().lower().split()
    if not parts:
        return True
    command = parts[0]
    if command in {"exit", "quit", "keluar"}:
        return False
    if command == "/help":
        print(HELP)
    elif command == "/spec":
        print(assistant.system.get_specs()["message"])
    elif command == "/status":
        print(assistant.status())
    elif command == "/mode":
        if len(parts) > 1 and parts[1] in {"auto", "local", "cloud"}:
            assistant.mode = parts[1]
            print(f"Mode diubah menjadi {assistant.mode}.")
        else:
            print("Pemakaian: /mode auto | local | cloud")
    else:
        print(assistant.handle(raw))
    return True


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    assistant = Assistant(ROOT)
    argv = sys.argv[1:]

    if argv:
        if argv[0].startswith("/") or argv[0].lower() in {"exit", "quit", "keluar"}:
            run_command(assistant, " ".join(argv))
        else:
            print(assistant.handle(" ".join(argv)))
        return

    print("Limbo siap. Ketik /help untuk bantuan, 'exit' untuk keluar.")
    while True:
        try:
            raw = input("anda> ")
        except (EOFError, KeyboardInterrupt):
            print("\nSampai jumpa.")
            break
        if not run_command(assistant, raw):
            print("Sampai jumpa.")
            break


if __name__ == "__main__":
    main()
