#!/usr/bin/env bash
# Stop Vanessa (both desktop overlay and background servers)

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if [ -f data/vanessa_desktop.pid ]; then
    PID=$(cat data/vanessa_desktop.pid)
    kill "$PID" > /dev/null 2>&1
    rm -f data/vanessa_desktop.pid
fi

if [ -f data/vanessa.pid ]; then
    PID=$(cat data/vanessa.pid)
    kill "$PID" > /dev/null 2>&1
    rm -f data/vanessa.pid
fi

pkill -f "python.*vanessa_desktop.py" > /dev/null 2>&1
pkill -f "python.*main.py" > /dev/null 2>&1

notify-send -a "Vanessa" "Vanessa Desconectada" "Hasta pronto, Amo Víctor."
echo "✨ Vanessa se ha detenido por completo."
