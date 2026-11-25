"""Otak cloud: Gemini API. Dipanggil hanya bila otak lokal tidak cukup."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request


class CloudUnavailable(Exception):
    """API key tidak ada, kuota habis, atau request gagal."""


class CloudBrain:
    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, config: dict, persona: str, specs: dict):
        self.enabled = bool(config.get("enabled", True))
        self.key_env = config.get("api_key_env", "GEMINI_API_KEY")
        self.model = config.get("model", "gemini-2.5-flash")
        self.grounding_model = config.get("grounding_model", self.model)
        self.fallback_models = [
            item for item in config.get("fallback_models", [])
            if item != self.model and item != self.grounding_model
        ]
        self.timeout = int(config.get("timeout", 30))
        self.persona = persona
        self.specs = specs
        self.allow_images = bool(config.get("allow_image_upload", False))

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.key_env, "").strip() or None

    def available(self) -> bool:
        return self.enabled and self.api_key is not None

    def _build_system(self, fresh: bool) -> str:
        context = (
            "\n\nKonteks mesin pengguna: "
            f"{self.specs.get('cpu', '-')}, RAM {self.specs.get('ram_gb', '-')} GB, "
            f"GPU {self.specs.get('gpu', '-')}. "
            + ("Gunakan Google Search grounding dan sertakan sumber jika memungkinkan."
               if fresh else "")
        )
        return self.persona + context

    def _post(self, payload: dict, fresh: bool = False) -> str:
        key = self.api_key
        if not self.enabled:
            raise CloudUnavailable("Otak cloud dinonaktifkan di config.json.")
        if not key:
            raise CloudUnavailable(
                f"API key belum diset. Set environment variable {self.key_env} terlebih dahulu."
            )

        primary = self.grounding_model if fresh else self.model
        models = [primary] + self.fallback_models
        body: dict = {}
        last_busy = False

        for index, model in enumerate(models):
            endpoint = self.ENDPOINT.format(model=model) + f"?key={key}"
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
                detail = exc.read().decode("utf-8", "replace")[:300]
                if exc.code in (429, 403):
                    raise CloudUnavailable(
                        f"Kuota/akses Gemini habis atau ditolak (HTTP {exc.code}). "
                        "Coba lagi nanti atau pakai otak lokal."
                    ) from exc
                if exc.code == 503:
                    last_busy = True
                    if index < len(models) - 1:
                        continue
                    raise CloudUnavailable(
                        "Gemini sedang padat (HTTP 503) pada semua model yang dicoba. "
                        "Coba lagi beberapa saat atau pakai otak lokal."
                    ) from exc
                if exc.code == 404:
                    if index < len(models) - 1:
                        continue
                    raise CloudUnavailable(
                        "Model Gemini di config.json tidak tersedia untuk akun ini (HTTP 404). "
                        "Coba ganti 'model' di config.json ke gemini-3.5-flash."
                    ) from exc
                raise CloudUnavailable(f"Gemini API error HTTP {exc.code}: {detail}") from exc
            except (urllib.error.URLError, OSError, ValueError) as exc:
                last_busy = True
                if index < len(models) - 1:
                    continue
                raise CloudUnavailable(
                    f"Gagal menghubungi Gemini API pada semua model yang dicoba: {exc}"
                ) from exc

        if not body:
            raise CloudUnavailable("Gemini tidak mengembalikan respons." + (" (503)" if last_busy else ""))

        try:
            parts = body["candidates"][0]["content"]["parts"]
            text_result = "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise CloudUnavailable("Respons Gemini tidak bisa dibaca.") from exc

        sources = self._extract_sources(body)
        if sources:
            text_result += "\n\nSumber:\n" + "\n".join(f"- {s}" for s in sources[:5])
        return text_result or "(Gemini mengembalikan jawaban kosong.)"

    def answer(self, text: str, fresh: bool = False) -> str:
        payload: dict = {
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "systemInstruction": {"parts": [{"text": self._build_system(fresh)}]},
        }
        if fresh:
            payload["tools"] = [{"google_search": {}}]
        return self._post(payload, fresh=fresh)

    def vision(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        """Kirim satu gambar ke Gemini untuk dideskripsikan."""
        if not self.allow_images:
            raise CloudUnavailable(
                "Upload gambar sedang NONAKTIF. Jika gambar kamu boleh dikirim ke API gratis, "
                "ubah 'allow_image_upload' menjadi true di config.json."
            )
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
            "systemInstruction": {"parts": [{"text": self._build_system(False)}]},
        }
        return self._post(payload, fresh=False)

    @staticmethod
    def _extract_sources(body: dict) -> list[str]:
        sources: list[str] = []
        try:
            metadata = body["candidates"][0]["groundingMetadata"]
            for chunk in metadata.get("groundingChunks", []):
                web = chunk.get("web", {})
                if web.get("uri"):
                    sources.append(f"{web.get('title', web['uri'])} — {web['uri']}")
        except (KeyError, IndexError, TypeError):
            pass
        return sources
