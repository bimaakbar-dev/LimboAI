"""Jembatan cloud gratis: Google AI Studio (Gemini) + Groq.

Tugas berat / info terbaru dieskalasi ke sini. Tidak ada infrastruktur berbayar.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request


class CloudUnavailable(Exception):
    """API key tidak ada, kuota habis, atau request gagal."""


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


class CloudBridge:
    def __init__(self, config: dict, persona: str, specs: dict):
        self.enabled = bool(config.get("enabled", True))
        self.key_env = config.get("api_key_env", "GEMINI_API_KEY")
        self.model = config.get("model", "gemini-2.5-flash")
        self.grounding_model = config.get("grounding_model", self.model)
        self.fallback_models = [
            item for item in config.get("fallback_models", [])
            if item != self.model and item != self.grounding_model
        ]
        self.timeout = int(config.get("timeout", 60))
        self.persona = persona
        self.specs = specs
        self.allow_images = bool(config.get("allow_image_upload", False))
        self.groq_key = os.environ.get("GROQ_API_KEY", "").strip() or None

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.key_env, "").strip() or None

    def available(self) -> bool:
        return bool(self.enabled and (self.api_key or self.groq_key))

    def provider(self) -> str:
        if self.groq_key:
            return "groq"
        if self.api_key:
            return "gemini"
        return "none"

    def _build_system(self, fresh: bool = False) -> str:
        context = (
            "\n\nKonteks mesin pengguna: "
            f"{self.specs.get('cpu', '-')}, RAM {self.specs.get('ram_gb', '-')} GB, "
            f"GPU {self.specs.get('gpu', '-')}. "
            + ("Gunakan Google Search grounding dan sertakan sumber. " if fresh else "")
        )
        return self.persona + context

    def answer(self, text: str, fresh: bool = False) -> str:
        if self.groq_key and not fresh:
            return self._ask_groq(text)
        return self._ask_gemini(text, fresh=fresh)

    # ---------- Groq ----------
    def _ask_groq(self, text: str) -> str:
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": self._build_system()},
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
        except (
            urllib.error.HTTPError, urllib.error.URLError, OSError, KeyError, ValueError
        ) as exc:
            if self.api_key:
                return self._ask_gemini(text, fresh=False)
            raise CloudUnavailable(f"Groq gagal: {exc}") from exc

    # ---------- Gemini ----------
    def _ask_gemini(self, text: str, fresh: bool = False) -> str:
        key = self.api_key
        if not self.enabled:
            raise CloudUnavailable("Otak cloud dinonaktifkan di config.json.")
        if not key:
            raise CloudUnavailable(
                f"API key belum diset. Set environment variable {self.key_env}."
            )
        payload: dict = {
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "systemInstruction": {"parts": [{"text": self._build_system(fresh)}]},
        }
        if fresh:
            payload["tools"] = [{"google_search": {}}]
        return self._post_gemini(payload, fresh)

    def _post_gemini(self, payload: dict, fresh: bool) -> str:
        key = self.api_key
        primary = self.grounding_model if fresh else self.model
        models = [primary] + self.fallback_models
        body: dict = {}

        for index, model in enumerate(models):
            endpoint = GEMINI_URL.format(model=model) + f"?key={key}"
            request = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 403):
                    raise CloudUnavailable(
                        f"Kuota/akses Gemini habis (HTTP {exc.code})."
                    ) from exc
                if exc.code in (503, 404) and index < len(models) - 1:
                    continue
                raise CloudUnavailable(f"Gemini HTTP {exc.code}") from exc
            except (urllib.error.URLError, OSError, ValueError) as exc:
                if index < len(models) - 1:
                    continue
                raise CloudUnavailable(f"Gemini gagal: {exc}") from exc

        try:
            parts = body["candidates"][0]["content"]["parts"]
            result = "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise CloudUnavailable("Respons Gemini tidak bisa dibaca.") from exc
        return result or "(Gemini mengembalikan jawaban kosong.)"

    def vision(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        if not self.allow_images:
            raise CloudUnavailable("Upload gambar NONAKTIF di config.json.")
        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                    }},
                ],
            }],
            "systemInstruction": {"parts": [{"text": self._build_system()}]},
        }
        return self._post_gemini(payload, fresh=False)
