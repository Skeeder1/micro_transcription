#!/bin/bash
# Script de redémarrage - Système de Dictée Vocale v2.0
# Arrête puis relance l'application

echo "🔄 Redémarrage du Système de Dictée Vocale..."
echo ""

# Aller dans le répertoire du script
cd "$(dirname "$0")" || exit 1

# Étape 1: Arrêter l'application
echo "[1/2] Arrêt de l'application..."
./stop.sh

# Attendre que tout soit bien arrêté
sleep 2

# Étape 2: Relancer l'application
echo ""
echo "[2/2] Relancement de l'application..."
./start.sh
