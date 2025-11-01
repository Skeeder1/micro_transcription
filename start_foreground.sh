#!/bin/bash
# Script de lancement en MODE FOREGROUND
# Garde le processus attaché au terminal pour supporter:
# - Hotkey F9 (accès au clavier X11)
# - Logs visibles en temps réel
# - Contrôle via Ctrl+C

echo "================================================"
echo "🎤 Système de Dictée Vocale - MODE FOREGROUND"
echo "================================================"
echo ""
echo "Fonctionnalités actives:"
echo "  ✓ Transcription temps réel"
echo "  ✓ Hotkey F9 (veille/actif)"
echo "  ✓ Visualiseur Qt6"
echo "  ✓ Logs en direct"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""
echo "================================================"
echo ""

# Aller dans le répertoire du projet
cd "$(dirname "$0")" || exit 1

# Arrêter toute instance précédente
./stop.sh >/dev/null 2>&1

# Vérifier l'environnement virtuel
if [ ! -f ".venv/bin/python3" ] && [ ! -f ".venv/bin/python" ]; then
    echo "❌ Erreur: Environnement virtuel introuvable!"
    echo "   Exécutez: python3 -m venv .venv"
    exit 1
fi

# Déterminer l'exécutable Python
if [ -f ".venv/bin/python3" ]; then
    PYTHON_EXE=".venv/bin/python3"
else
    PYTHON_EXE=".venv/bin/python"
fi

# Lancer en mode foreground (premier plan)
# Les logs s'affichent dans le terminal ET sont sauvegardés
exec $PYTHON_EXE main.py 2>&1 | tee /tmp/transcription_$(date +%Y%m%d_%H%M%S).log
