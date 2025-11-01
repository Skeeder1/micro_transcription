#!/bin/bash
# Script d'arret pour le systeme de transcription v2.0
# Tue tous les processus Python lies a l'application

echo "Arret du systeme de transcription..."

# Trouver et tuer les processus main.py
MAIN_PIDS=$(pgrep -f "python.*main.py")
if [ -n "$MAIN_PIDS" ]; then
    echo "   Arret du processus principal (PID: $MAIN_PIDS)..."
    kill $MAIN_PIDS 2>/dev/null
    sleep 1

    # Verification si le processus est toujours la
    if pgrep -f "python.*main.py" >/dev/null; then
        echo "   Force kill du processus principal..."
        kill -9 $(pgrep -f "python.*main.py") 2>/dev/null
    fi
fi

# Trouver et tuer les processus du visualiseur
VIS_PIDS=$(pgrep -f "python.*ui.visualizer_app")
if [ -n "$VIS_PIDS" ]; then
    echo "   Arret du visualiseur (PID: $VIS_PIDS)..."
    kill $VIS_PIDS 2>/dev/null
    sleep 1

    # Verification si le processus est toujours la
    if pgrep -f "python.*ui.visualizer_app" >/dev/null; then
        echo "   Force kill du visualiseur..."
        kill -9 $(pgrep -f "python.*ui.visualizer_app") 2>/dev/null
    fi
fi

# Nettoyer les fichiers de logs temporaires anciens (plus de 7 jours)
if [ -d "/tmp" ]; then
    find /tmp -name "transcription_*.log" -mtime +7 -delete 2>/dev/null
fi

echo "   [OK] Systeme arrete"
