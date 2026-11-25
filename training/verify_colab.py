"""Verifikasi dataset base64 di notebook Colab bisa di-decode kembali."""
from __future__ import annotations

import base64
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
notebook = json.loads((HERE / "train_lora_colab.ipynb").read_text(encoding="utf-8"))
source = "".join(notebook["cells"][2]["source"])

chunks: list[str] = []
for line in source.splitlines():
    stripped = line.strip().strip(",").strip('"')
    if stripped and all(char in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for char in stripped):
        chunks.append(stripped)

decoded = base64.b64decode("".join(chunks))
expected = (HERE / "dataset.jsonl").read_bytes()
print("sel:", len(notebook["cells"]))
print("decode byte:", len(decoded))
print("sama dengan dataset.jsonl:", decoded == expected)
print("contoh baris:", decoded.decode("utf-8").splitlines()[0][:90])
