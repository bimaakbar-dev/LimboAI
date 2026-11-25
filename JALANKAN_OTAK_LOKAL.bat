@echo off
cd /d "%~dp0"
title Limbo - Otak Lokal (llama.cpp)

echo Menyalakan otak lokal Limbo di port 8080...
.\llama\llama-server.exe -m models\qwen2.5-3b-instruct-q4_k_m.gguf --lora adapter\limbo-lora.gguf --port 8080 -c 4096
