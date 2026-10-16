DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

mkdir -p data

if [ -f data/vanessa_desktop.pid ]; then
    OLD_PID=$(cat data/vanessa_desktop.pid)
    kill "$OLD_PID" > /dev/null 2>&1
    rm -f data/vanessa_desktop.pid
fi
pkill -f "python.*vanessa_desktop.py" > /dev/null 2>&1

echo "Iniciando Vanessa en su pantalla (Modo Overlay Nativo)..."
setsid nohup "$DIR/.venv/bin/python" -u "$DIR/vanessa_desktop.py" >> "$DIR/data/vanessa_desktop.log" 2>&1 &
PID=$!
disown -h $PID
echo $PID > "$DIR/data/vanessa_desktop.pid"

sleep 3
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✨ Vanessa ha aparecido en su pantalla flotando sobre sus ventanas (PID: $PID)."
    notify-send -a "Vanessa" "Vanessa está en su pantalla" "A su servicio, Amo Víctor. Haga clic derecho sobre ella para configuraciones."
else
    echo "Error al iniciar Vanessa Desktop. Revisa data/vanessa_desktop.log"
fi
