"""Dataset untuk melatih otak router: intent + keputusan lokal/cloud."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

SYSTEM = (
    "Kamu adalah router otak AI Limbo. Balas HANYA JSON valid dengan kunci "
    "intent, route, reason, escalation_prompt. route='local' untuk tugas ringan, "
    "route='cloud' untuk penalaran berat atau info terbaru."
)

LOCAL = [
    ("cek spesifikasi pc", "system_info"),
    ("cek sisa disk", "disk_check"),
    ("lihat isi folder", "file_list"),
    ("baca file catatan", "file_read"),
    ("hitung hash file", "hash"),
    ("cari file duplikat", "duplicate"),
    ("cek proses cpu", "process"),
    ("cek koneksi internet", "network"),
    ("rename file a jadi b", "file_rename"),
    ("pindahkan file", "file_move"),
    ("halo", "greeting"),
    ("siapa kamu", "identity"),
    ("terima kasih", "thanks"),
]

CLOUD = [
    ("jelaskan panjang soal arsitektur microservice", "deep_explanation"),
    ("analisis mendalam dataset ini", "analysis"),
    ("riset tren AI terbaru", "research"),
    ("bandingkan dua framework", "comparison"),
    ("bantu debug kode panjang ini", "coding"),
    ("tulis program lengkap", "coding"),
    ("harga gpu hari ini", "fresh_info"),
    ("berita teknologi terbaru", "fresh_info"),
    ("versi terbaru library", "fresh_info"),
    ("dokumentasi api terbaru", "fresh_info"),
]

VARIANTS = [
    "{text}",
    "tolong {text}",
    "bisa {text}?",
    "{text} ya",
    "coba {text}",
]


def main() -> None:
    records = []
    for text, intent in LOCAL:
        for variant in VARIANTS:
            prompt = variant.format(text=text)
            answer = {
                "intent": intent,
                "route": "local",
                "reason": "tugas ringan, cukup diproses lokal",
                "escalation_prompt": "",
            }
            records.append({"messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
            ]})

    for text, intent in CLOUD:
        for variant in VARIANTS:
            prompt = variant.format(text=text)
            answer = {
                "intent": intent,
                "route": "cloud",
                "reason": "penalaran berat atau informasi terbaru",
                "escalation_prompt": prompt,
            }
            records.append({"messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
            ]})

    target = HERE / "dataset.jsonl"
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Dataset router ditulis: {target} ({len(records)} contoh)")


if __name__ == "__main__":
    main()
