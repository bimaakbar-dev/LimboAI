@echo off
cd /d "%~dp0"
title Limbo - Otak Lokal (CPU-only)

set "LORA=adapter\limbo-lora.gguf"
if exist "adapter\skill-asisten-ringan.gguf" set "LORA=adapter\skill-asisten-ringan.gguf"

if not exist "models\qwen2.5-3b-instruct-q4_k_m.gguf" (
  echo Model dasar belum ada. Jalankan: python download_model.py
  pause
  exit /b 1
)
if not exist "%LORA%" (
  echo Adapter belum ada: %LORA%
  echo Latih di Colab lalu taruh adapter .gguf di folder adapter\
  pause
  exit /b 1
)

echo Menyalakan otak lokal (CPU-only, n_gpu_layers=0)...
echo Adapter: %LORA%
.\llama\llama-server.exe -m models\qwen2.5-3b-instruct-q4_k_m.gguf --lora "%LORA%" --n-gpu-layers 0 --port 8080 -c 4096
