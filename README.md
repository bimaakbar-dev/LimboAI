# Limbo — Desktop AI Companion

Asisten pribadi yang jalan di PC ber-spesifikasi rendah. Otak kecil di lokal,
tugas berat dieskalasi ke AI cloud gratis. Avatar melayang di desktop.

---

## 1. Spesifikasi & batasan (wajib dipatuhi)

| Komponen | Nilai | Aturan |
|---|---|---|
| CPU | i5-3570, 4 core, AVX (tanpa AVX2) | CPU-only |
| RAM | 16 GB DDR3 | Model lokal maks 2,5 GB |
| GPU | GT 710 2 GB | **Tidak dipakai**, `n_gpu_layers=0` |
| OS | Windows 10 64-bit | — |

Dilarang: CUDA, torch, tensorflow, model >3B, model vision/generatif lokal.

---

## 2. Cara pakai (paling penting)

### A. Nyalakan otak lokal (opsional tapi disarankan)
```
JALANKAN_OTAK_LOKAL.bat
```
Memuat `qwen2.5-3b-instruct-q4_k_m.gguf` + adapter LoRA di port **8080**, CPU-only.

### B. Nyalakan avatar + chat
```
JALANKAN_LIMBO_HUD.bat
```
Jendela transparan tanpa border, selalu di atas desktop.

### C. CLI teks (tanpa avatar)
```
python asisten.py
```

Perintah di CLI: `/spec`, `/status`, `/mode auto|local|cloud`, `/help`, `exit`.

---

## 3. Perilaku avatar

| Kondisi | Posisi |
|---|---|
| Desktop kosong (Win+D) | Besar di tengah |
| Ada aplikasi terbuka | Kecil di kanan atas |

- Klik avatar (tanpa drag) → buka chat
- Drag → pindah posisi
- Tutup chat: klik avatar lagi / klik luar / **Esc**
- Warna: hitam + putih, glow biru **hanya di avatar**
- Chatbox: satu frame rounded putih, aksen hitam, isi: avatar → bubble → textbox
- Animasi mengikuti **status AI**, bukan diputar acak

---

## 4. Struktur folder

```
asisten-pc/
├─ README.md              ← kamu sedang baca ini
├─ config.json            model, timeout, mode, API
├─ PERSONA.md             identitas & aturan Limbo
├─ .env.example           template GEMINI_API_KEY + GROQ_API_KEY
├─ requirements.txt       SDK cloud (opsional, ringan)
├─ asisten.py             CLI
├─ hud_qt.py              Desktop companion (PyQt6 WebEngine)
├─ hud_server.py          API lokal: /api/chat, /api/state, /api/status
├─ hud_state.py           jembatan status AI → avatar
├─ hud_web/               avatar + chat (engine GrokBot asli)
│  └─ vendor/             grok-player.js + grok-recipes.json
├─ brain/                 OTAK AI
│  ├─ local_llm.py        llama.cpp CPU-only
│  ├─ cloud_bridge.py     Gemini + Groq (free tier)
│  └─ router.py           lokal vs cloud
├─ core/
│  ├─ assistant.py        orkestrator + skill selector
│  ├─ spec_guard.py       capability guard
│  ├─ tool_descriptions.py
│  └─ router.py           deteksi tool (regex)
├─ tools/                 file & system tool
├─ skills/                sistem skill
├─ colab_training/        latih router spesialis
├─ training/              latih adapter asisten & skill
├─ pipeline/              metadata stock (DI-HOLD)
├─ tests/                 13 tes otomatis
├─ models/                GGUF (diabaikan git)
├─ llama/                 binary llama.cpp (diabaikan git)
├─ adapter/               hasil LoRA (diabaikan git)
└─ grokbot-src/           source ZIP (diabaikan git)
```

---

## 5. Alur otak

```
Input
  ↓
brain/router.py → ringan? lokal : berat? cloud
  ↓                         ↓
LocalLLM (CPU)        CloudBridge (Gemini/Groq)
  ↓                         ↓
JSON tool call        jawaban/escalation
  ↓
core/assistant.py → tool / skill / jawaban
  ↓
hud_state.json → avatar berubah state
```

Cloud memakai **Groq** kalau `GROQ_API_KEY` ada, otherwise **Gemini**.

---

## 6. Training (semua di Google Colab, gratis, T4)

| Kebutuhan | Notebook |
|---|---|
| Latih otak router | `colab_training/finetune_router.ipynb` |
| Latih adapter asisten | `training/train_lora_colab.ipynb` |
| Latih skill ringan | `skills/asisten-ringan/train.ipynb` |
| Konversi → GGUF | `training/convert_limbo_colab.ipynb` atau `skills/asisten-ringan/convert.ipynb` |

Cara umum: buka notebook di Colab → Runtime → T4 GPU → Run all → download `.zip` →
konversi → taruh `.gguf` di `adapter/`.

Dataset sudah tertanam di notebook, tidak perlu upload manual.

---

## 7. Skill

`core/assistant.py` memilih skill lewat `skills/registry.py` sebelum menjawab.

Skill aktif: **`asisten-ringan`** (file/folder, disk, proses, hash, duplikat, guard).
Detail di `skills/README.md`.

---

## 8. Auto-start

Belum dipasang. Setelah semua final:
```
powershell -ExecutionPolicy Bypass -File PASANG_AUTOSTART.ps1
```

---

## 9. Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| Mode lokal gagal | `llama-server` tidak jalan | Jalankan `JALANKAN_OTAK_LOKAL.bat` |
| `timeout` di lokal | CPU lambat | `config.json` → `local.timeout = 60` |
| Cloud 429 | Kuota habis | Pakai Groq gratis atau tunggu |
| Avatar tidak muncul | HUD mati | Jalankan `JALANKAN_LIMBO_HUD.bat` |
| Chat input tidak bisa diklik | mode drag aktif | Tutup & buka chat lagi |

---

## 10. Backup

Jangan commit `models/`, `llama/`, `adapter/`, token/API key — semuanya sudah ada di `.gitignore`.
Gunakan GitHub Releases / Git LFS kalau mau backup bobot model.

Repository: https://github.com/bimaakbar-dev/LimboAI
