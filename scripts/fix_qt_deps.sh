#!/bin/bash
# Script pour installer les dépendances Qt manquantes sur Ubuntu
# Corrige l'erreur: "xcb-cursor0 or libxcb-cursor0 is needed"

echo "================================================"
echo "Installation des dépendances Qt manquantes"
echo "================================================"
echo ""

# Vérifier qu'on a les droits sudo
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Ce script doit être exécuté avec sudo"
    echo "   Utilisation: sudo bash $0"
    exit 1
fi

echo "[1/2] Mise à jour des dépôts APT..."
apt update

echo ""
echo "[2/2] Installation de libxcb-cursor0..."
apt install -y libxcb-cursor0

echo ""
echo "================================================"
echo "✅ Dépendances Qt installées avec succès!"
echo "================================================"
echo ""
echo "Vous pouvez maintenant lancer l'application:"
echo "  ./start_debug.sh"
echo ""
