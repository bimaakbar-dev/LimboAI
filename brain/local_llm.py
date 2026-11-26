"""Wrapper SLM lokal: llama.cpp / llama-server, CPU-only.

Aturan hardware: n_gpu_layers = 0, model GGUF 1B-3B, Q4_K_M / Q5_K_M.
Tidak memakai torch / CUDA.
"""
from __future__ import annotations

from core.local_brain import LocalBrain, build_plan_system


class LocalLLM(LocalBrain):
    """Client ke llama-server dengan batasan CPU-only."""

    def __init__(self, config: dict, persona: str):
        super().__init__(config, persona)
        # Pastikan tidak ada offload GPU.
        self.n_gpu_layers = 0

    @staticmethod
    def hardware_note() -> str:
        return "CPU-only · llama.cpp · GGUF 1B-3B · Q4_K_M · n_gpu_layers=0"


__all__ = ["LocalLLM", "build_plan_system"]
