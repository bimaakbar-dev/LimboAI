"""Buat notebook Colab untuk mengonversi adapter Limbo (safetensors) ke GGUF."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": text.strip().splitlines(keepends=True),
    }


CELLS = [
    md("""
# Konversi adapter Limbo → GGUF

Upload `asisten-lora.zip` (hasil training Colab), lalu notebook ini menghasilkan
`limbo-lora.gguf` untuk dipakai `llama-server --lora`.

Tidak perlu GPU. Runtime CPU cukup.
"""),
    code("""
from google.colab import files
import zipfile, os

print("Upload asisten-lora.zip:")
uploaded = files.upload()
name = next(iter(uploaded))

with zipfile.ZipFile(name) as archive:
    archive.extractall("/content")

adapter = "/content/asisten-lora"
print("Isi adapter:", sorted(os.listdir(adapter)))
"""),
    code("""
!git clone --depth 1 -q https://github.com/ggml-org/llama.cpp /content/llama.cpp
!pip -q install gguf transformers safetensors
print("Siap.")
"""),
    code("""
!python /content/llama.cpp/convert_lora_to_gguf.py \
    --base-model-id Qwen/Qwen2.5-3B-Instruct \
    --outtype f16 \
    /content/asisten-lora \
    --outfile /content/limbo-lora.gguf
"""),
    code("""
from google.colab import files

size = os.path.getsize("/content/limbo-lora.gguf")
print("limbo-lora.gguf:", size, "byte")
files.download("/content/limbo-lora.gguf")
"""),
    md("""
Taruh `limbo-lora.gguf` di folder PC:
```
asisten-pc/adapter/limbo-lora.gguf
```
Lalu jalankan:
```
.\\llama\\llama-server.exe -m models\\qwen2.5-3b-instruct-q4_k_m.gguf --lora adapter\\limbo-lora.gguf --port 8080 -c 4096
```
"""),
]

for index, cell in enumerate(CELLS):
    cell["id"] = f"convert-{index}"

notebook = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

target = HERE / "convert_limbo_colab.ipynb"
target.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Notebook konversi ditulis: {target}")
