"""Buat notebook Colab mandiri: dataset disisipkan sebagai base64 di dalam notebook."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip().splitlines(keepends=True),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(HERE / "dataset.jsonl"))
    parser.add_argument("--out", default=str(HERE / "train_lora_colab.ipynb"))
    parser.add_argument("--name", default="limbo-lora")
    args = parser.parse_args()

    raw = Path(args.dataset).read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    chunks = [encoded[i:i + 8000] for i in range(0, len(encoded), 8000)]
    b64_literal = "\n".join(f'    "{chunk}"' for chunk in chunks)

    cells = [
        md(f"""
# Latih Asisten PC — LoRA di Google Colab (T4 gratis)

Notebook ini **sudah mengandung dataset**, jadi tidak perlu upload file apa pun.

## Cara
1. **Runtime → Change runtime type → Hardware accelerator: T4 GPU**
2. Runtime → Run all
3. Di akhir, file `{args.name}.zip` akan ter-download otomatis.

Tanpa kartu kredit. Kalau T4 tidak tersedia, coba lagi nanti atau ganti ke model Flash/CPU saat runtime tersedia.
"""),
        code("""
import os, torch
print("torch:", torch.__version__)
print("CUDA:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    raise RuntimeError("Pilih Runtime → Change runtime type → T4 GPU sebelum Run all.")
"""),
        code(f"""
import base64

B64_CHUNKS = [
{b64_literal}
]
with open("/content/dataset.jsonl", "wb") as f:
    f.write(base64.b64decode("".join(B64_CHUNKS)))
print("Dataset siap:", os.path.getsize("/content/dataset.jsonl"), "byte")
"""),
        code("""
!pip -q install -U transformers peft accelerate
"""),
        code("""
import json, torch
from pathlib import Path
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    Trainer, TrainingArguments, DataCollatorForSeq2Seq,
)
from peft import LoraConfig, get_peft_model

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
MAX_LEN = 640

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

records = [
    json.loads(line)
    for line in Path("/content/dataset.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
print("Jumlah contoh:", len(records))

class SFTData(Dataset):
    def __init__(self, rows, tok, max_len):
        self.examples = []
        for row in rows:
            messages = row["messages"]
            prompt = tok.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True)
            answer = messages[-1]["content"] + tok.eos_token
            p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
            a_ids = tok(answer, add_special_tokens=False)["input_ids"]
            ids = (p_ids + a_ids)[:max_len]
            labels = ([-100] * len(p_ids) + a_ids)[:max_len]
            if len(ids) >= 16:
                self.examples.append({
                    "input_ids": ids,
                    "attention_mask": [1] * len(ids),
                    "labels": labels,
                })
    def __len__(self):
        return len(self.examples)
    def __getitem__(self, index):
        return self.examples[index]

train_data = SFTData(records, tokenizer, MAX_LEN)
print("Contoh ter-tokenisasi:", len(train_data))
"""),
        code("""
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    device_map={"": 0},
    torch_dtype=torch.float16,
)
model.config.use_cache = False

lora = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)
model = get_peft_model(model, lora)
model.print_trainable_parameters()
"""),
        code("""
from transformers import TrainingArguments

# Argumen seminimal mungkin: kompatibel dengan transformers versi terbaru.
args = TrainingArguments(
    output_dir="/content/asisten-out",
    num_train_epochs=2,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    logging_steps=20,
    save_strategy="no",
    report_to="none",
    seed=42,
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_data,
    data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100),
)
trainer.train()
"""),
        code(f"""
import torch

OUT = "/content/{args.name}"
model.save_pretrained(OUT)
tokenizer.save_pretrained(OUT)
print("Adapter tersimpan:", OUT)

system = "Kamu adalah asisten PC. Balas HANYA JSON valid dengan kunci tool, args, dan answer."
prompt = tokenizer.apply_chat_template(
    [
        {{"role": "system", "content": system}},
        {{"role": "user", "content": "cek spec pc"}},
    ],
    tokenize=False,
    add_generation_prompt=True,
)
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
with torch.no_grad():
    output = model.generate(
        **inputs, max_new_tokens=120, do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
print(tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))
"""),
        code(f"""
import os, zipfile

zip_path = "/content/{args.name}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
    for root, _, names in os.walk(OUT):
        for name in names:
            full = os.path.join(root, name)
            archive.write(full, os.path.relpath(full, "/content"))

print("ZIP dibuat:", zip_path, os.path.getsize(zip_path), "byte")
try:
    from google.colab import files
    files.download(zip_path)
except Exception as exc:
    print("Kalau download gagal, ambil manual dari panel Files:", zip_path, exc)
"""),
    ]

    for index, cell in enumerate(cells):
        cell["id"] = f"colab-{index}"

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "accelerator": "GPU",
            "colab": {"provenance": []},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Notebook Colab ditulis: {target} ({len(cells)} sel, dataset {len(raw)} byte)")


if __name__ == "__main__":
    main()
