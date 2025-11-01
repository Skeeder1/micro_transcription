#!/bin/bash
# Script d'installation des dépendances Python
# Crée le venv et installe toutes les dépendances

echo "================================================"
echo "Installation des dépendances Python"
echo "================================================"
echo ""

# Aller dans le répertoire du projet
cd "$(dirname "$0")/.." || exit 1

# Vérifier que Python3 est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 n'est pas installé!"
    echo "   Installation: sudo apt install python3 python3-venv"
    exit 1
fi

# Créer l'environnement virtuel s'il n'existe pas
if [ ! -d ".venv" ]; then
    echo "[1/4] Création de l'environnement virtuel..."
    python3 -m venv .venv
    echo "   ✅ Environnement virtuel créé"
else
    echo "[1/4] Environnement virtuel existant détecté"
fi

echo ""

# Activer l'environnement virtuel
echo "[2/4] Activation de l'environnement virtuel..."
source .venv/bin/activate

# Mettre à jour pip
echo ""
echo "[3/4] Mise à jour de pip..."
pip install --upgrade pip

# Installer les dépendances
echo ""
echo "[4/4] Installation des dépendances Python..."
echo "   (Cela peut prendre 2-3 minutes, surtout pour faster-whisper)"
echo ""

pip install flask
pip install faster-whisper
pip install PySide6
pip install pyperclip
pip install pynput
pip install numpy
pip install sounddevice

echo ""
echo "================================================"
echo "✅ Dépendances Python installées avec succès!"
echo "================================================"
echo ""
echo "Vous pouvez maintenant:"
echo "  1. Tester l'installation: bash scripts/test_ubuntu_setup.sh"
echo "  2. Lancer l'application:  bash scripts/start_transcription_debug.sh"
