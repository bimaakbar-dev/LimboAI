# Latih Limbo (Phase 3 — LoRA di Google Colab)

**Limbo** adalah nama AI kita. Folder ini berisi dataset dan notebook untuk melatih perilaku
model lokal `Qwen2.5-3B-Instruct` agar menjadi asisten PC kita.

Kaggle tidak dipakai karena kernelnya tetap memakai image CPU meski GPU T4 dipilih.

## File

| File | Fungsi |
|---|---|
| `dataset.jsonl` | 310 contoh (tool call, guard, percakapan identitas) |
| `generate_dataset.py` | Generator dataset |
| `train_lora_colab.ipynb` | Notebook training Colab (dataset sudah tertanam) |
| `make_colab_notebook.py` | Generator notebook training |
| `convert_limbo_colab.ipynb` | Notebook konversi adapter → `limbo-lora.gguf` |
| `make_convert_colab.py` | Generator notebook konversi |
| `verify_colab.py` | Cek integritas dataset yang tertanam |

## Training

1. Buka https://colab.research.google.com
2. **File → Upload notebook** → `training/train_lora_colab.ipynb`
3. **Runtime → Change runtime type → T4 GPU**
4. **Runtime → Run all**
5. Di akhir, `limbo-lora.zip` otomatis ter-download

Tidak perlu upload dataset — 310 contoh sudah ditanam di dalam notebook.

## Konversi ke GGUF

1. Buka notebook `training/convert_limbo_colab.ipynb` di Colab
2. Upload `limbo-lora.zip`
3. Run all → `limbo-lora.gguf` ter-download
4. Taruh di `asisten-pc/adapter/limbo-lora.gguf`

## Pakai di PC

```powershell
JALANKAN_OTAK_LOKAL.bat
JALANKAN_LIMBO_HUD.bat
```

## Perbaikan dataset terakhir

Dataset sekarang punya jawaban identitas yang benar:
- `siapa kamu?` → "Saya Limbo..."
- `saya siapa?` → "Kamu adalah pengguna PC ini..."

Training ulang perlu dilakukan supaya model lokal mengikuti jawaban ini.
