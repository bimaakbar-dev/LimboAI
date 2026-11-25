"""Daftar tool yang boleh dipanggil model lokal. Dipakai bersama oleh runtime dan dataset."""

TOOL_NAMES = [
    "get_specs", "disk_usage", "processes", "internet_check",
    "list_dir", "file_info", "read_text", "hash_file", "find_duplicates",
    "write_csv", "rename_batch", "move_file", "run_command",
]

TOOL_DESCRIPTIONS = """TOOL YANG TERSEDIA:
- get_specs(): tampilkan CPU, RAM, GPU, OS, dan disk PC
- disk_usage(path="C:\\\\"): cek ruang disk suatu path
- processes(limit=15): tampilkan proses dengan CPU tertinggi
- internet_check(): cek apakah internet tersedia
- list_dir(path="workspace"): lihat isi folder
- file_info(path): info ukuran dan tipe sebuah file
- read_text(path): baca isi file teks
- hash_file(path, algo="sha256"): hitung hash file
- find_duplicates(path="workspace"): cari file duplikat berdasarkan hash
- write_csv(path, rows, header, overwrite): tulis file CSV
- rename_batch(path, mapping, confirm, dry_run): rename banyak file (butuh konfirmasi)
- move_file(src, dst, confirm, dry_run): pindah file (butuh konfirmasi)
- run_command(argv, confirm): jalankan perintah dari daftar whitelist (butuh konfirmasi)

Catatan: generate_metadata SEDANG DINONAKTIFKAN. Jangan memanggilnya."""
