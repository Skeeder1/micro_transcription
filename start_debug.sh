#!/bin/bash
# Script de lancement DEBUG simplifié - Système de Dictée Vocale v2.0
# Lance avec logs visibles dans le terminal

echo "🎤 Démarrage du Système en MODE DEBUG..."
echo ""

# Aller dans le répertoire du script
cd "$(dirname "$0")" || exit 1

# Appeler le script de lancement debug
bash scripts/start_transcription_debug.sh
