"""Otak lokal: llama.cpp / llama-server, CPU-only.

Hardware: i5-3570 (AVX, tanpa AVX2), GT 710 tidak dipakai.
Aturan: n_gpu_layers=0, GGUF 1B-3B, Q4_K_M/Q5_K_M, tanpa torch/CUDA.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request


class LocalUnavailable(Exception):
    """llama-server tidak aktif atau tidak merespons."""


def build_plan_system(persona: str, tool_descriptions: str) -> str:
    """System prompt identik untuk runtime dan dataset training."""
    return (
        persona
        + "\n\nKamu harus memilih tool yang tersedia. Balas HANYA dengan JSON valid "
        "tanpa penjelasan lain, format:\n"
        '{"tool": "nama_tool", "args": {...}, "answer": "ringkasan singkat"}\n'
        "Jika tidak ada tool yang cocok, pakai {\"tool\": null, \"args\": {}, "
        '"answer": "jawaban"}. Jangan mengarang argumen.\n\n'
        + tool_descriptions
    )


class LocalLLM:
    """Client OpenAI-compatible ke llama-server di 127.0.0.1:8080."""

    def __init__(self, config: dict, persona: str):
        self.enabled = bool(config.get("enabled", True))
        self.base = config.get("base_url", "http://127.0.0.1:8080").rstrip("/")
        self.timeout = int(config.get("timeout", 60))
        self.model_label = config.get("model_label", "model-local")
        self.max_tokens = int(config.get("max_tokens", 256))
        self.temperature = float(config.get("temperature", 0.2))
        self.persona = persona
        self.n_gpu_layers = 0  # hardware constraint

    @staticmethod
    def hardware_note() -> str:
        return "CPU-only · llama.cpp · GGUF 1B-3B · Q4_K_M · n_gpu_layers=0"

    def available(self) -> bool:
        if not self.enabled:
            return False
        try:
            with urllib.request.urlopen(
                self.base + "/health", timeout=min(self.timeout, 3)
            ) as response:
                return response.status == 200
        except Exception:
            return False

    def _chat(self, user_text: str, system: str) -> str:
        if not self.enabled:
            raise LocalUnavailable("Otak lokal dinonaktifkan di config.json.")
        payload = {
            "model": self.model_label,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        request = urllib.request.Request(
            self.base + "/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
        except (
            urllib.error.URLError, OSError, KeyError, ValueError, IndexError
        ) as exc:
            raise LocalUnavailable(str(exc)) from exc

    def answer(self, text: str) -> str:
        return self._chat(text, self.persona)

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            value = json.loads(cleaned[start:end + 1])
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None

    def plan(self, text: str, tool_descriptions: str) ->dict | None:
        return self._parse_json(
            self._chat(text, build_plan_system(self.persona, tool_descriptions))
        )
