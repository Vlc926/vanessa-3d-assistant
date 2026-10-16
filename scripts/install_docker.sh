#!/bin/bash
set -e

echo "Instalando paquetes de Docker y Docker Compose para CachyOS / Arch..."
pacman -Sy --needed --noconfirm docker docker-compose docker-buildx

echo "Habilitando e iniciando el servicio systemd de Docker..."
systemctl enable --now docker

if [ -n "$SUDO_USER" ]; then
    TARGET_USER="$SUDO_USER"
elif [ -n "$PKEXEC_UID" ]; then
    TARGET_USER=$(id -nu "$PKEXEC_UID")
else
    TARGET_USER="$USER"
fi

echo "Agregando usuario $TARGET_USER al grupo docker..."
usermod -aG docker "$TARGET_USER"

echo "Verificación de Docker:"
docker --version
docker compose version

echo "Instalación completada con éxito."
