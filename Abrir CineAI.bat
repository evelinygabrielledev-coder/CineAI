@echo off
rem Abre o CineAI sem precisar do terminal (clique duas vezes neste arquivo).
cd /d "%~dp0"
rem O modelo de embeddings ja esta baixado: nao precisa consultar a internet (abre mais rapido).
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
start "" pythonw main.py
