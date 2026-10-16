#!/usr/bin/env bash
# Start Vanessa in the background (no open terminal required)

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

mkdir -p data

# Check if already running
if [ -f data/vanessa.pid ]; then
    OLD_PID=$(cat data/vanessa.pid)
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Vanessa ya está corriendo en segundo plano (PID: $OLD_PID)."
        notify-send -a "Vanessa" "Vanessa ya está activa" "Panel disponible en http://127.0.0.1:8765"
        exit 0
    fi
fi

# Kill any stray previous instance on port 8765
fuser -k 8765/tcp > /dev/null 2>&1

echo "Iniciando Vanessa en segundo plano..."
nohup "$DIR/.venv/bin/python" -u "$DIR/main.py" >> "$DIR/data/vanessa.log" 2>&1 &
PID=$!
echo $PID > "$DIR/data/vanessa.pid"

sleep 3
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✨ Vanessa ha iniciado con éxito en segundo plano (PID: $PID)."
    notify-send -a "Vanessa" "Vanessa está lista" "A su servicio, Amo Víctor. Panel: http://127.0.0.1:8765"
else
    echo "Error al iniciar Vanessa. Revisa data/vanessa.log"
fi
