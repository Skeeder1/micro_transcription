#!/bin/bash
# Script d'installation des dépendances système Ubuntu
# Doit être exécuté avec sudo

echo "================================================"
echo "Installation des dépendances système Ubuntu"
echo "================================================"
echo ""

# Vérifier qu'on a les droits sudo
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Ce script doit être exécuté avec sudo"
    echo "   Utilisation: sudo bash $0"
    exit 1
fi

# Mise à jour des dépôts
echo "[1/2] Mise à jour des dépôts APT..."
apt update

# Installation des dépendances
echo ""
echo "[2/2] Installation des dépendances..."
apt install -y \
    xdotool \
    xclip \
    xsel \
    portaudio19-dev \
    libxcb-xinerama0 \
    python3-venv \
    imagemagick

echo ""
echo "================================================"
echo "✅ Dépendances système installées avec succès!"
echo "================================================"
echo ""
echo "Vous pouvez maintenant lancer:"
echo "  bash scripts/install_python_deps.sh"
