#!/usr/bin/env bash
# Launcher for Lumina / Jarvis Assistant

cd "$(dirname "$0")"

echo "=========================================================="
echo "  🚀 INICIANDO LUMINA - ASISTENTE PERSONAL TIPO JARVIS"
echo "=========================================================="

if [ ! -d ".venv" ]; then
    echo "Configurando entorno virtual..."
    uv venv --python 3.12
    uv sync
fi

# Run assistant server
.venv/bin/python main.py
