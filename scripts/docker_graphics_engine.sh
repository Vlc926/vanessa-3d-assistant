#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/docker/docker-compose.yml"

COMMAND="${1:-status}"

run_docker() {
    if docker "$@" 2>/dev/null; then
        return 0
    elif command -v newgrp &>/dev/null; then
        newgrp docker <<EOF
docker $*
EOF
    else
        return 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        return 1
    fi
    if ! run_docker info &> /dev/null; then
        return 1
    fi
    return 0
}

case "$COMMAND" in
    start)
        if check_docker; then
            echo "Iniciando motor gráfico Vanessa en Docker con límites de recursos (512M RAM, 1.0 CPU)..."
            run_docker compose -f "$COMPOSE_FILE" up -d --build
            echo "Motor gráfico en Docker activo en puerto 8899."
        else
            echo "Iniciando fallback local nativo en segundo plano..."
            python3 -u "$ROOT_DIR/deploy/docker/engine_server.py" 8899 "$ROOT_DIR" &
            echo "Motor local activo en puerto 8899."
        fi
        ;;
    stop)
        if check_docker; then
            echo "Deteniendo contenedor de motor gráfico..."
            run_docker compose -f "$COMPOSE_FILE" down
        fi
        pkill -f "engine_server.py" || true
        echo "Motor gráfico detenido."
        ;;
    status)
        if check_docker; then
            echo "=== Estado de Contenedores Vanessa ==="
            run_docker compose -f "$COMPOSE_FILE" ps
            echo "=== Consumo de Recursos ==="
            run_docker stats --no-stream vanessa_graphics_engine 2>/dev/null || echo "Contenedor no activo."
        else
            echo "Docker no disponible. Comprobando servicio local en puerto 8899..."
            if ss -tulpn | grep -q ":8899"; then
                echo "Servidor de motor activo en puerto 8899."
            else
                echo "Servidor de motor no activo."
            fi
        fi
        ;;
    build)
        if check_docker; then
            echo "Construyendo imagen del motor gráfico..."
            run_docker compose -f "$COMPOSE_FILE" build
        fi
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|build}"
        exit 1
        ;;
esac
