# Skill Pattern — Limbo

AI tetap satu (core), tapi **kemampuan dipecah jadi skill**. Sebelum menjawab,
`core/assistant.py` memanggil `skills/registry.select_skill(text)` untuk memilih skill
berdasarkan topik.

## Skill pertama: `asisten-ringan`

Fokus: pekerjaan ringan di PC ini — file/folder, disk, proses, hash, duplikat,
konfirmasi, dan capability guard. Tidak termasuk training/render berat.

| File | Fungsi |
|---|---|
| `manifest.json` | Daftar skill + keyword + path dataset/adapter |
| `registry.py` | Pemilih skill berdasarkan keyword |
| `build_dataset.py` | Buat dataset skill dari dataset utama |
| `asisten-ringan/dataset.jsonl` | 190 contoh khusus skill ini |
| `asisten-ringan/train.ipynb` | Notebook Colab untuk latih adapter skill |
| `asisten-ringan/convert.ipynb` | Notebook konversi adapter skill → `skill-asisten-ringan.gguf` |

## Latih skill

1. Buka `skills/asisten-ringan/train.ipynb` di https://colab.research.google.com
2. Runtime → **T4 GPU**
3. Run all
4. Download `skill-asisten-ringan.zip`
5. Buka `skills/asisten-ringan/convert.ipynb` di Colab, upload `skill-asisten-ringan.zip`,
   Run all → ter-download `skill-asisten-ringan.gguf`
6. Taruh di `asisten-pc/adapter/skill-asisten-ringan.gguf`

## Pakai adapter skill

Ubah `JALANKAN_OTAK_LOKAL.bat` agar memuat skill adapter:
```
.\llama\llama-server.exe -m models\qwen2.5-3b-instruct-q4_k_m.gguf --lora adapter\skill-asisten-ringan.gguf --port 8080 -c 4096
```

## Menambah skill baru

1. Tambah entri di `manifest.json`
2. Buat dataset di folder skill (bisa pakai `build_dataset.py` sebagai template)
3. Generate notebook:
   ```
   python training/make_colab_notebook.py --dataset skills/<nama>/dataset.jsonl --out skills/<nama>/train.ipynb --name skill-<nama>
   ```
4. Latih di Colab, konversi, lalu daftarkan adapter path di manifest
