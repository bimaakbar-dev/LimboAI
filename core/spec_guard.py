"""Capability guard: menolak tugas yang melampaui kemampuan PC."""
from __future__ import annotations


HEAVY_KEYWORDS = [
    "latih", "training", "train ", "fine-tune", "finetune", "fine tuning",
    "melatih", "training model", "render 3d", "render video", "video 4k",
    "llama 70", "llama 65", "gpt-oss-120", "stable diffusion", "text-to-video",
    "cuda compile", "kompilasi kernel", "deep learning dari nol",
]

FRESH_KEYWORDS = [
    "terbaru", "terkini", "hari ini", "sekarang", "saat ini", "versi ",
    "harga", "berita", "update", "dokumentasi", "changelog", "rilis",
    "cuaca", "kurs", "apakah sudah", "sedang berlangsung",
]

VISION_KEYWORDS = [
    "gambar", "foto", "image", "metadata stock", "adobe stock",
    "keyword gambar", "judul gambar", "lihat gambar",
]

LOCAL_KEYWORDS = [
    "cek spec", "spesifikasi", "cek disk", "ruang disk", "storage",
    "proses", "folder", "direktori", "rename", "pindah", "salinn", "copy",
    "hash", "duplikat", "daftar file", "isi folder", "baca file", "csv",
]


class SpecGuard:
    """Mengklasifikasikan permintaan berdasarkan batas kemampuan mesin."""

    def __init__(self, specs: dict):
        self.specs = specs

    @staticmethod
    def _contains(text: str, keywords: list[str]) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in keywords)

    def complaint(self) -> str:
        specs = self.specs
        return (
            "Maaf, saya tidak bisa menjalankan itu di PC ini.\n"
            f"Spesifikasi saat ini: {specs.get('cpu', '-')}, "
            f"RAM {specs.get('ram_gb', '-')} GB, "
            f"GPU {specs.get('gpu', '-')} ({specs.get('gpu_vram_gb', '-')} GB VRAM).\n"
            "Untuk pekerjaan seberat itu, gunakan Kaggle Notebook atau Google Colab "
            "(T4 gratis, tanpa kartu kredit). Saya hanya bisa melakukan tugas ringan "
            "seperti mengelola file, sistem, dan info teks."
        )

    def classify(self, text: str) -> dict:
        lowered = text.lower()
        heavy = self._contains(text, HEAVY_KEYWORDS)

        # Penjelasan tentang training di cloud boleh lewat jalur cloud.
        informational = (
            self._contains(text, ["cara", "gimana", "bagaimana", "bisakah", "bisa "])
            and self._contains(text, ["colab", "kaggle", "cloud", "gratis"])
        )
        if heavy and not informational:
            return {"route": "reject", "reason": "heavy_task", "message": self.complaint()}

        if self._contains(text, VISION_KEYWORDS):
            return {
                "route": "cloud",
                "reason": "vision_needed",
                "message": "Membutuhkan model vision di cloud.",
            }

        if self._contains(text, FRESH_KEYWORDS):
            return {
                "route": "cloud",
                "reason": "fresh_info",
                "message": "Membutuhkan informasi terbaru dari internet.",
            }

        if self._contains(text, LOCAL_KEYWORDS):
            return {
                "route": "tool",
                "reason": "local_operation",
                "message": "Bisa ditangani locally.",
            }

        return {
            "route": "local_llm",
            "reason": "conversation",
            "message": "Percakapan umum; otak lokal mencoba menjawab.",
        }
