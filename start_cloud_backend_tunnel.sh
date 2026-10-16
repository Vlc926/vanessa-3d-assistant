#!/usr/bin/env bash
# ==============================================================================
# Vanessa - Servidor Cloud Backend + Túnel Seguro Cloudflare (Background Daemon)
# 100% Gratuito | Cero Tarjetas | Cero Planes de Pago | Cifrado Militar
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")"

PID_FILE="/tmp/vanessa_cloud_server.pid"
TUNNEL_PID_FILE="/tmp/vanessa_tunnel.pid"
TUNNEL_LOG="/tmp/vanessa_tunnel.log"

echo "=========================================================="
echo "🌸 Iniciando Vanessa Cloud Backend & Túnel Seguro..."
echo "=========================================================="

# 1. Iniciar servidor FastAPI con nohup y disown
pkill -f "server_cloud.py" 2>/dev/null || true
sleep 1

echo "🚀 Levantando server_cloud.py..."
setsid .venv/bin/python server_cloud.py < /dev/null > /tmp/vanessa_server.log 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "✅ Servidor activo con PID: $SERVER_PID"

sleep 3

# 2. Iniciar Túnel Cloudflare para obtener URL HTTPS mundial
echo "🌐 Conectando túnel seguro con Cloudflare..."
pkill -f "cloudflared tunnel" 2>/dev/null || true
rm -f "$TUNNEL_LOG"

setsid "$HOME/.local/bin/cloudflared" tunnel --url http://localhost:8765 < /dev/null > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!
echo "$TUNNEL_PID" > "$TUNNEL_PID_FILE"

echo "⏳ Esperando asignación de URL pública segura..."
PUBLIC_URL=""
for i in {1..20}; do
    if [ -f "$TUNNEL_LOG" ]; then
        URL=$(grep -o 'https://[-a-zA-Z0-9@:%._\+~#=]*\.trycloudflare\.com' "$TUNNEL_LOG" | head -n 1 || true)
        if [ -n "$URL" ]; then
            PUBLIC_URL="$URL"
            break
        fi
    fi
    sleep 1
done

if [ -n "$PUBLIC_URL" ]; then
    echo "=========================================================="
    echo "🎉 ¡SERVIDOR EN LÍNEA Y SEGURO EN TODO EL MUNDO!"
    echo "🔗 Tu URL pública HTTPS es: $PUBLIC_URL"
    echo "=========================================================="
    echo "📍 Endpoints listos para vincular en tus aplicaciones:"
    echo "   - WhatsApp Webhook: $PUBLIC_URL/api/v1/omni/whatsapp"
    echo "   - Telegram Webhook: $PUBLIC_URL/api/v1/omni/telegram"
    echo "   - Facebook Webhook: $PUBLIC_URL/api/v1/omni/meta"
    echo "   - Estado y Gemelo Digital: $PUBLIC_URL/api/v1/omni/status"
    echo "=========================================================="
    
    # Auto-conectar el cliente local al túnel
    sleep 3
    ./connect_to_cloud.sh "$PUBLIC_URL"
else
    echo "⚠️ No se pudo obtener la URL del túnel automáticamente. Revisa $TUNNEL_LOG"
fi
