"""Buat notebook Colab untuk mengonversi adapter safetensors → GGUF."""
from __future__ import annotations

import argparse
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="limbo-lora")
    parser.add_argument("--out", default=str(HERE / "convert_limbo_colab.ipynb"))
    args = parser.parse_args()

    cells = [
        md(f"""
# Konversi adapter {args.name} → GGUF

Upload `{args.name}.zip` (hasil training Colab), lalu notebook ini menghasilkan
`{args.name}.gguf` untuk dipakai `llama-server --lora`.

Tidak perlu GPU. Runtime CPU cukup.
"""),
        code(f"""
from google.colab import files
import zipfile, os

print("Upload {args.name}.zip:")
uploaded = files.upload()
name = next(iter(uploaded))

with zipfile.ZipFile(name) as archive:
    archive.extractall("/content")

adapter = "/content/{args.name}"
print("Isi adapter:", sorted(os.listdir(adapter)))
"""),
        code("""
!git clone --depth 1 -q https://github.com/ggml-org/llama.cpp /content/llama.cpp
!pip -q install gguf transformers safetensors
print("Siap.")
"""),
        code(f"""
!python /content/llama.cpp/convert_lora_to_gguf.py \\
    --base-model-id Qwen/Qwen2.5-3B-Instruct \\
    --outtype f16 \\
    /content/{args.name} \\
    --outfile /content/{args.name}.gguf
"""),
        code(f"""
from google.colab import files

size = os.path.getsize("/content/{args.name}.gguf")
print("{args.name}.gguf:", size, "byte")
files.download("/content/{args.name}.gguf")
"""),
        md(f"""
Taruh `{args.name}.gguf` di folder PC:
```
asisten-pc/adapter/{args.name}.gguf
```
Lalu jalankan:
```
.\\llama\\llama-server.exe -m models\\qwen2.5-3b-instruct-q4_k_m.gguf --lora adapter\\{args.name}.gguf --port 8080 -c 4096
```
"""),
    ]

    for index, cell in enumerate(cells):
        cell["id"] = f"convert-{index}"

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "colab": {"provenance": []},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Notebook konversi ditulis: {target}")


if __name__ == "__main__":
    main()
