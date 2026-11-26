"""Router otak: lokal untuk ringan, cloud untuk penalaran berat / info terbaru."""
from __future__ import annotations

CLOUD_KEYWORDS = [
    "jelaskan panjang", "analisis mendalam", "riset", "bandingkan", "coding",
    "debug", "tulis program", "makalah", "terbaru", "hari ini", "harga",
    "berita", "dokumentasi", "versi", "cuaca", "kurs", "carilah di internet",
]

LOCAL_KEYWORDS = [
    "spec", "spesifikasi", "disk", "folder", "file", "hash", "duplikat",
    "proses", "internet", "rename", "pindah", "baca", "csv", "konfirmasi",
    "halo", "siapa", "terima kasih",
]


class BrainRouter:
    def __init__(self, local, cloud):
        self.local = local
        self.cloud = cloud

    def decide(self, text: str) -> dict:
        lowered = text.lower()
        local_ok = self.local.available()
        cloud_ok = self.cloud.available()

        heavy = any(keyword in lowered for keyword in CLOUD_KEYWORDS)
        light = any(keyword in lowered for keyword in LOCAL_KEYWORDS)

        if heavy:
            return {
                "target": "cloud" if cloud_ok else ("local" if local_ok else "offline"),
                "reason": "penalaran/info terbaru",
                "confidence": 0.9,
            }
        if light:
            return {
                "target": "local" if local_ok else ("cloud" if cloud_ok else "offline"),
                "reason": "tugas ringan / lokal",
                "confidence": 0.85,
            }
        return {
            "target": "local" if local_ok else ("cloud" if cloud_ok else "offline"),
            "reason": "default",
            "confidence": 0.6,
        }
