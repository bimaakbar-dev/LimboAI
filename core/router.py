"""Penentu jalur: tool lokal -> otak lokal -> Gemini API."""
from __future__ import annotations

import re
from typing import Any


TOOL_PATTERNS: list[tuple[str, str, dict[str, Any]]] = [
    (r"(metadata|adobe stock|keyword.*gambar|judul.*gambar|deskripsi gambar)", "generate_metadata", {}),
    (r"(cek|lihat|tampilkan).*(spec|spesifikasi|\bpc\b|komputer)", "get_specs", {}),
    (r"(cek|lihat|tampilkan).*(disk|storage|ruang)", "disk_usage", {"path": "C:\\"}),
    (r"(proses|cpu tertinggi|task yang jalan)", "processes", {}),
    (r"(daftar|isi|list|lihat).*(folder|direktori)", "list_dir", {}),
    (r"\bhash\b", "hash_file", {}),
    (r"duplikat", "find_duplicates", {"path": "workspace"}),
    (r"(baca|isi).*(file|teks)", "read_text", {}),
    (r"(internet|online|koneksi)", "internet_check", {}),
    (r"(jalankan|run)\s", "run_command", {}),
    (r"(tulis|simpan|buat).*csv", "write_csv", {}),
    (r"(rename|ganti nama|ubah nama)", "rename_batch", {}),
    (r"pindah(kan)?\s", "move_file", {}),
    (r"(info|detail)\s+file", "file_info", {}),
]


def extract_path(text: str) -> str | None:
    quoted = re.search(r"[\"']([^\"']+)[\"']", text)
    if quoted:
        return quoted.group(1)
    named = re.search(r"\b(?:folder|direktori)\s+([^\s]+)", text, re.IGNORECASE)
    if named is None:
        named = re.search(r"\b(?:file|path)\s+([^\s]+)", text, re.IGNORECASE)
    return named.group(1) if named else None


def match_tool(text: str) -> tuple[str, dict[str, Any]] | None:
    lowered = text.lower()
    for pattern, tool, defaults in TOOL_PATTERNS:
        if re.search(pattern, lowered):
            args = dict(defaults)
            path = extract_path(text)
            if path and tool in {"list_dir", "hash_file", "read_text", "find_duplicates"}:
                args["path"] = path
            if tool == "run_command":
                match = re.search(r"(?:jalankan|run)\s+(.+)", text, re.IGNORECASE)
                if match:
                    args["argv"] = match.group(1).split()
            if tool == "rename_batch":
                match = re.search(
                    r"(\S+\.\S+)\s+(?:jadi|menjadi|ke|->)\s+(\S+\.\S+)", text, re.IGNORECASE
                )
                if match:
                    args["mapping"] = {match.group(1): match.group(2)}
                if path := extract_path(text):
                    args["path"] = path
            if tool == "move_file":
                parts = re.findall(r"\S+\.\S+", text)
                if len(parts) >= 2:
                    args["src"], args["dst"] = parts[0], parts[1]
            return tool, args
    return None


class Router:
    def __init__(self, local_brain, cloud_brain):
        self.local = local_brain
        self.cloud = cloud_brain

    def decide(self, text: str, guard_result: dict) -> dict:
        if guard_result["route"] == "reject":
            return {"route": "reject", "reason": guard_result["reason"]}

        detected = match_tool(text)
        if detected:
            return {"route": "tool", "tool": detected[0], "args": detected[1]}

        wants_cloud = guard_result["route"] == "cloud"
        local_ok = self.local.available()
        cloud_ok = self.cloud.available()

        if wants_cloud and cloud_ok:
            return {"route": "cloud", "fresh": guard_result["reason"] == "fresh_info"}
        if local_ok:
            return {"route": "local_llm"}
        if cloud_ok:
            return {"route": "cloud", "fresh": guard_result["reason"] == "fresh_info"}

        return {
            "route": "offline",
            "message": (
                "Otak lokal belum aktif (llama-server tidak berjalan) dan API key Gemini belum diset. "
                "Lihat README.md untuk cara mengaktifkan keduanya."
            ),
        }
