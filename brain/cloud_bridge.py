"""Jembatan ke AI Cloud gratis: Google AI Studio (Gemini) / Groq.

Tugas berat dieskalasi ke sini. Tidak ada infrastruktur berbayar.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from core.cloud_brain import CloudBrain

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


class CloudBridge(CloudBrain):
    """Gemini + fallback Groq. Pilih penyedia yang tersedia."""

    def __init__(self, config: dict, persona: str, specs: dict):
        super().__init__(config, persona, specs)
        self.groq_key = os.environ.get("GROQ_API_KEY", "").strip() or None

    def available(self) -> bool:
        return super().available() or self.groq_key is not None

    def provider(self) -> str:
        if self.groq_key:
            return "groq"
        if super().available():
            return "gemini"
        return "none"

    def answer(self, text: str, fresh: bool = False) -> str:
        if self.groq_key and not fresh:
            return self._ask_groq(text)
        return super().answer(text, fresh=fresh)

    def _ask_groq(self, text: str) -> str:
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": self._build_system(False)},
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        request = urllib.request.Request(
            GROQ_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.groq_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, KeyError, ValueError) as exc:
            if super().available():
                return super().answer(text, fresh=False)
            raise RuntimeError(f"Groq/Gemini gagal: {exc}") from exc
