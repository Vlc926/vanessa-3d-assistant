#!/usr/bin/env bash
# ==============================================================================
# Vanessa - Conectar Computadora Local al Servidor en la Nube (Paso 3 Automático)
# Uso: ./connect_to_cloud.sh <IP_DEL_SERVIDOR_O_DOMINIO> [TOKEN_OPCIONAL]
# ==============================================================================

if [ -z "${1:-}" ]; then
    echo "⚠️ Uso: $0 <IP_O_DOMINIO_DEL_SERVIDOR> [TOKEN]"
    echo "Ejemplo: $0 129.151.78.20"
    echo "Ejemplo con dominio: $0 https://vanessa.midominio.com mi_token_secreto"
    exit 1
fi

SERVER_TARGET="$1"
AUTH_TOKEN="${2:-vanessa_super_secret_token_12345}"
CONFIG_FILE="config/cloud_config.json"

# Formatear URL
if [[ "$SERVER_TARGET" =~ ^https?:// ]]; then
    PUBLIC_URL="$SERVER_TARGET"
    HOST_IP=$(echo "$SERVER_TARGET" | sed -e 's|^[^/]*//||' -e 's|/.*$||' -e 's|:.*$||')
else
    PUBLIC_URL="http://${SERVER_TARGET}:8765"
    HOST_IP="$SERVER_TARGET"
fi

echo "=========================================================="
echo "🌸 Vinculando Vanessa Local con Servidor en la Nube..."
echo "📍 Dirección del Servidor: $PUBLIC_URL"
echo "🔑 Token de Autenticación: $AUTH_TOKEN"
echo "=========================================================="

# Modificar config/cloud_config.json con python para no romper formato JSON
python3 -c "
import json

path = '$CONFIG_FILE'
try:
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
except Exception:
    cfg = {}

cfg.setdefault('server', {})
cfg['server']['host'] = '0.0.0.0'
cfg['server']['port'] = 8765
cfg['server']['auth_token'] = '$AUTH_TOKEN'
cfg['server']['public_url'] = '$PUBLIC_URL'

with open(path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=4, ensure_ascii=False)

print('✅ config/cloud_config.json actualizado correctamente.')
"

# Probar conexión al endpoint de salud
echo "📡 Verificando conexión en vivo con el servidor remoto..."
HEALTH_URL="${PUBLIC_URL}/api/v1/omni/status"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$HEALTH_URL" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo "🎉 ¡CONEXIÓN EXITOSA! El servidor remoto de Vanessa está activo y respondiendo."
    echo "🚀 Puedes iniciar Vanessa localmente con: ./start.sh"
else
    echo "⚠️ Atención: El servidor respondió con código HTTP $HTTP_STATUS (o no está accesible aún)."
    echo "   Asegúrate de que 'server_cloud.py' o Docker estén corriendo en el servidor y el puerto 8765 esté abierto."
fi
echo "=========================================================="
