#!/usr/bin/env bash
# ==============================================================================
# Vanessa AI Maid - Script de Aprovisionamiento Automático para Servidor Remoto
# Diseñado para: Ubuntu 22.04 / 24.04 LTS o Debian en Oracle Cloud / VPS Gratuito
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo "🌸 Instalando y configurando Servidor Seguro para Vanessa..."
echo "=========================================================="

# 1. Actualizar repositorios e instalar paquetes base
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl git ufw fail2ban htop unzip

# 2. Configurar Firewall seguro (UFW)
echo "🛡️ Configurando Firewall UFW (Seguridad y Privacidad Estricta)..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8765/tcp
sudo ufw --force enable

# 3. Instalar Docker y Docker Compose si no existen
if ! command -v docker &> /dev/null; then
    echo "🐳 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker "$USER"
    rm get-docker.sh
fi

# 4. Clonar o preparar directorio de Vanessa
DEPLOY_DIR="$HOME/vanessa_server"
mkdir -p "$DEPLOY_DIR"

echo "✅ Servidor preparado con éxito."
echo "Para arrancar Vanessa en la nube:"
echo "1. Coloca tus archivos de jarvis_assistant en $DEPLOY_DIR"
echo "2. Ejecuta: cd $DEPLOY_DIR/deploy && docker compose up -d --build"
echo "=========================================================="
