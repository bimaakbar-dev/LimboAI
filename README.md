# Limbo — Desktop AI Companion

AI pribadi yang berjalan di PC ini. Target: asisten ringan, avatar melayang, tanpa kerja berat.

## Spesifikasi PC
Intel Core i5-3570 (4 core) · RAM 16 GB · NVIDIA GT 710 2 GB · Windows 10 64-bit.

## Menjalankan

```powershell
JALANKAN_OTAK_LOKAL.bat   # opsional: llama-server + LoRA di port 8080
JALANKAN_LIMBO_HUD.bat    # avatar companion + chat
```

CLI teks:
```powershell
python asisten.py
```

## Struktur utama

| File | Fungsi |
|---|---|
| `asisten.py` | CLI asisten |
| `core/assistant.py` | Orkestrator + capability guard + skill selector |
| `core/router.py` | Tool -> lokal -> cloud |
| `core/local_brain.py` | Client llama.cpp |
| `core/cloud_brain.py` | Gemini API (fallback) |
| `hud_qt.py` | PyQt6 frameless + transparan + drag + Esc + auto-close |
| `hud_server.py` | `/api/chat`, `/api/state`, `/api/status`, `/api/layout` |
| `hud_state.py` | Jembatan status AI -> avatar |
| `hud_web/` | Avatar + chat (engine GrokBot asli dari ZIP kamu) |
| `grokbot-src/` | Source `grokbot-animation-anatomy-main.zip` |
| `skills/` | Skill pattern |
| `training/` | Dataset + notebook Colab |
| `adapter/` | `limbo-lora.gguf`, `limbo-lora/` |
| `models/` | `qwen2.5-3b-instruct-q4_k_m.gguf` |
| `llama/` | llama.cpp binaries |

## Avatar

- Body hitam, mata putih, **glow biru tipis hanya di avatar**
- Mengikuti **status AI**, bukan diputar bergiliran
- Desktop kosong (Win+D): besar di tengah · Ada aplikasi: kecil di kanan atas
- Klik avatar = buka chat · Drag = pindah · Esc / klik luar = tutup

## Chatbox

Satu frame rounded putih, aksen hitam, berisi:
```
avatar
bubble percakapan
textbox + tombol kirim
```
Tanpa panel setting.

## Otak AI (Hybrid Local-Cloud)

Sesuai batasan hardware: **CPU-only**, `n_gpu_layers=0`, GGUF 1B–3B Q4_K_M, tanpa torch/CUDA.

```
brain/
├── local_llm.py    → llama-server CPU-only (1B–3B GGUF)
├── cloud_bridge.py → Gemini + Groq (free tier)
└── router.py       → lokal untuk ringan, cloud untuk penalaran/info terbaru
```

`core/assistant.py` memakai `brain/` sebagai otak utama. Cloud otomatis memilih Groq
jika `GROQ_API_KEY` ada, kalau tidak Gemini.

Router spesialis dilatih dari `colab_training/dataset.jsonl` (115 contoh intent+route)
lewat `colab_training/finetune_router.ipynb` di Colab T4.

## Skill pattern

`core/assistant.py` memilih skill lewat `skills/registry.py` sebelum menjawab.

Skill pertama: **`asisten-ringan`** — file/folder, disk, proses, hash, duplikat,
konfirmasi, capability guard. Detail: `skills/README.md`.

```powershell
python skills/build_dataset.py
python training/make_colab_notebook.py --dataset skills/asisten-ringan/dataset.jsonl --out skills/asisten-ringan/train.ipynb --name skill-asisten-ringan
```

## Latih model

Training membersihkan perilaku via LoRA di Google Colab (T4 gratis, tanpa kartu kredit).
Detail: `training/README.md`.

```powershell
python training/generate_dataset.py
python training/make_colab_notebook.py
```

## Produksi microstock

Pipeline metadata (`metadata.py`) **di-hold** sesuai permintaan.

## Auto-start

Belum dipasang. Setelah semua final:
```powershell
powershell -ExecutionPolicy Bypass -File PASANG_AUTOSTART.ps1
```

Catatan: API key Kaggle yang pernah dibagikan di chat sebaiknya diregenerate.
