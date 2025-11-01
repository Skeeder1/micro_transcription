#!/bin/bash
# Script d'arrêt simplifié - Système de Dictée Vocale v2.0
# Appelle le script d'arrêt dans scripts/

echo "⏹️  Arrêt du Système de Dictée Vocale..."
echo ""

# Aller dans le répertoire du script
cd "$(dirname "$0")" || exit 1

# Appeler le script d'arrêt complet
bash scripts/stop_transcription.sh
