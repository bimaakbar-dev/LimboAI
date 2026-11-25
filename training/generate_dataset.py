"""Buat dataset JSONL untuk fine-tune perilaku asisten PC.

Output: training/dataset.jsonl
Format: {"messages": [system, user, assistant]}

Dataset ini mengajarkan model:
- memilih tool yang tepat (JSON seekor-sama seperti local_brain.plan)
- menolak tugas berat (capability guard)
- menjawab percakapan ringan tanpa tool
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.local_brain import build_plan_system  # noqa: E402
from core.spec_guard import SpecGuard
from core.tool_descriptions import TOOL_DESCRIPTIONS

TRAINING_DIR = Path(__file__).resolve().parent

COMPLAINT = SpecGuard({
    "cpu": "Intel(R) Core(TM) i5-3570 CPU @ 3.40GHz",
    "ram_gb": 15.96,
    "gpu": "NVIDIA GeForce GT 710",
    "gpu_vram_gb": 2.0,
}).complaint()

TOOL_EXAMPLES = [
    ("cek spec pc", {"tool": "get_specs", "args": {}, "answer": "Saya ambil spesifikasi PC."}),
    ("tampilkan spesifikasi komputer", {"tool": "get_specs", "args": {}, "answer": "Saya ambil spesifikasi PC."}),
    ("cek ruang disk", {"tool": "disk_usage", "args": {"path": "C:\\"}, "answer": "Saya cek ruang disk."}),
    ("berapa sisa ruang disk C", {"tool": "disk_usage", "args": {"path": "C:\\"}, "answer": "Saya cek ruang disk."}),
    ("proses dengan CPU tertinggi", {"tool": "processes", "args": {"limit": 15}, "answer": "Saya lihat proses yang berjalan."}),
    ("cek koneksi internet", {"tool": "internet_check", "args": {}, "answer": "Saya cek koneksi internet."}),
    ("lihat isi folder workspace", {"tool": "list_dir", "args": {"path": "workspace"}, "answer": "Saya lihat isi folder."}),
    ("daftar file di folder workspace", {"tool": "list_dir", "args": {"path": "workspace"}, "answer": "Saya lihat isi folder."}),
    ("info file catatan.txt", {"tool": "file_info", "args": {"path": "catatan.txt"}, "answer": "Saya ambil info file."}),
    ("baca isi file catatan.txt", {"tool": "read_text", "args": {"path": "catatan.txt"}, "answer": "Saya baca isi file."}),
    ("hash file foto.jpg", {"tool": "hash_file", "args": {"path": "foto.jpg", "algo": "sha256"}, "answer": "Saya hitung hash file."}),
    ("cari duplikat di folder workspace", {"tool": "find_duplicates", "args": {"path": "workspace"}, "answer": "Saya cari file duplikat."}),
    ("tulis csv hasil.csv", {"tool": "write_csv", "args": {"path": "workspace/hasil.csv", "rows": [], "header": ["Nama"], "overwrite": True}, "answer": "Saya tulis CSV."}),
    ("rename file a.txt jadi b.txt di folder workspace", {"tool": "rename_batch", "args": {"path": "workspace", "mapping": {"a.txt": "b.txt"}, "confirm": False, "dry_run": True}, "answer": "Rencana rename dibuat. Butuh konfirmasi."}),
    ("pindahkan file a.txt ke folder arsip", {"tool": "move_file", "args": {"src": "a.txt", "dst": "arsip/a.txt", "confirm": False, "dry_run": True}, "answer": "Rencana pemindahan dibuat. Butuh konfirmasi."}),
    ("jalankan tasklist", {"tool": "run_command", "args": {"argv": ["tasklist"], "confirm": False}, "answer": "Perintah perlu konfirmasi sebelum dijalankan."}),
]

GUARD_EXAMPLES = [
    ("latih model AI di PC ini", COMPLAINT),
    ("tolong training deep learning di komputer ini", COMPLAINT),
    ("jalankan fine tune llama 70b di sini", COMPLAINT),
    ("render video 4k pakai PC ini", COMPLAINT),
]

CHAT_EXAMPLES = [
    ("halo", "Halo! Saya Limbo, asisten PC kamu. Ada yang bisa saya bantu?"),
    ("siapa kamu?", "Saya Limbo, asisten pribadi yang berjalan di PC kamu. Saya bisa mengelola file, mengecek sistem, dan menjalankan perintah ringan."),
    ("kamu siapa?", "Saya Limbo, asisten PC milik kamu."),
    ("siapa nama kamu?", "Nama saya Limbo."),
    ("saya siapa?", "Kamu adalah pengguna PC ini. Saya belum tahu nama kamu kecuali kamu memberitahunya."),
    ("siapa saya?", "Kamu adalah pengguna PC tempat saya berjalan. Belum ada nama yang kamu berikan pada saya."),
    ("apakah kamu tahu nama saya?", "Belum. Kamu belum memberitahu nama kamu. Kalau mau, sebut saja dan saya akan mengingatnya selama percakapan ini."),
    ("terima kasih", "Sama-sama. Kalau ada lagi, tinggal bilang saja."),
    ("apa yang bisa kamu lakukan?", "Saya bisa mengecek spesifikasi dan disk, mengelola folder, menghitung hash, mencari duplikat, serta menjalankan perintah aman. Saya tidak melakukan pekerjaan berat seperti training model."),
    ("bisakah kamu melihat gambar?", "Tidak secara lokal. Model lokal saya hanya membaca teks. Untuk gambar dibutuhkan model vision di cloud."),
    ("bagaimana cara latih model di colab gratis?", "Gunakan Google Colab gratis, pilih runtime T4 GPU, lalu jalankan script fine-tuning dengan dataset kamu. PC ini hanya dipakai untuk menjalankan hasilnya."),
]


def variants(text: str) -> list[str]:
    return [
        text,
        f"tolong {text}",
        f"bisa {text}?",
        f"{text}?",
        f"{text} ya",
        f"aku mau {text}",
        f"coba {text}",
        f"hei, {text}",
        f"{text} dong",
        f"tolong bantu {text}",
    ]


def main() -> None:
    persona = (ROOT / "PERSONA.md").read_text(encoding="utf-8")
    system = build_plan_system(persona, TOOL_DESCRIPTIONS)

    records: list[dict] = []

    for user, payload in TOOL_EXAMPLES:
        answer = json.dumps(payload, ensure_ascii=False)
        for varied in variants(user):
            records.append({"messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": varied},
                {"role": "assistant", "content": answer},
            ]})

    for user, answer in GUARD_EXAMPLES + CHAT_EXAMPLES:
        payload = {"tool": None, "args": {}, "answer": answer}
        output = json.dumps(payload, ensure_ascii=False)
        for varied in variants(user):
            records.append({"messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": varied},
                {"role": "assistant", "content": output},
            ]})

    target = TRAINING_DIR / "dataset.jsonl"
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Dataset ditulis: {target}")
    print(f"Jumlah contoh: {len(records)}")


if __name__ == "__main__":
    main()
