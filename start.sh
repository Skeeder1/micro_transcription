#!/bin/bash
# Script de lancement simplifié - Système de Dictée Vocale v2.0
# Appelle le script principal dans scripts/

echo "🎤 Démarrage du Système de Dictée Vocale..."
echo ""

# Aller dans le répertoire du script
cd "$(dirname "$0")" || exit 1

# Appeler le script de lancement complet
bash scripts/start_transcription.sh
