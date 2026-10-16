#!/usr/bin/env bash
# Detener Vanessa Cloud Backend y Túnel Cloudflare
PID_FILE="/tmp/vanessa_cloud_server.pid"

echo "🛑 Deteniendo túnel y servidor de Vanessa..."
pkill -f "cloudflared tunnel --url http://localhost:8765" 2>/dev/null || true

if [ -f "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
fi

pkill -f "server_cloud.py" 2>/dev/null || true
echo "✅ Servidor detenido limpiamente."
