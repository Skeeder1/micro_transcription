#!/bin/bash
# Script de test pour valider l'installation Ubuntu
# Vérifie toutes les dépendances et la configuration

echo "================================================"
echo "Test de l'installation Ubuntu"
echo "Système de Dictée Vocale Avancé v2.0"
echo "================================================"
echo ""

# Compteurs
ERRORS=0
WARNINGS=0

# Fonction pour afficher les résultats
check_ok() {
    echo "✓ $1"
}

check_warn() {
    echo "⚠ $1"
    WARNINGS=$((WARNINGS + 1))
}

check_error() {
    echo "✗ $1"
    ERRORS=$((ERRORS + 1))
}

# 1. Vérifier l'OS
echo "[1/10] Vérification du système d'exploitation..."
if [ "$(uname)" = "Linux" ]; then
    check_ok "Système Linux détecté"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "    Distribution: $NAME $VERSION"
    fi
else
    check_error "Ce script est conçu pour Linux"
fi
echo ""

# 2. Vérifier Python
echo "[2/10] Vérification de Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    check_ok "Python installé: $PYTHON_VERSION"

    # Vérifier la version (minimum 3.8)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        check_ok "Version Python suffisante (>= 3.8)"
    else
        check_error "Python 3.8 ou supérieur requis"
    fi
else
    check_error "Python3 non installé"
    echo "    Installation: sudo apt install python3"
fi
echo ""

# 3. Vérifier l'environnement virtuel
echo "[3/10] Vérification de l'environnement virtuel..."
cd "$(dirname "$0")/.." || exit 1
if [ -d ".venv" ]; then
    check_ok "Environnement virtuel trouvé"

    if [ -f ".venv/bin/python" ] || [ -f ".venv/bin/python3" ]; then
        check_ok "Exécutable Python présent dans .venv"
    else
        check_error "Exécutable Python absent de .venv"
    fi
else
    check_error "Environnement virtuel non trouvé"
    echo "    Création: python3 -m venv .venv"
fi
echo ""

# 4. Vérifier les dépendances Python
echo "[4/10] Vérification des dépendances Python..."
if [ -f ".venv/bin/python" ] || [ -f ".venv/bin/python3" ]; then
    PYTHON_EXE=".venv/bin/python3"
    [ ! -f "$PYTHON_EXE" ] && PYTHON_EXE=".venv/bin/python"

    # Flask
    if $PYTHON_EXE -c "import flask" 2>/dev/null; then
        check_ok "Flask installé"
    else
        check_error "Flask non installé (pip install flask)"
    fi

    # faster-whisper
    if $PYTHON_EXE -c "import faster_whisper" 2>/dev/null; then
        check_ok "faster-whisper installé"
    else
        check_error "faster-whisper non installé (pip install faster-whisper)"
    fi

    # PySide6
    if $PYTHON_EXE -c "import PySide6" 2>/dev/null; then
        check_ok "PySide6 installé"
    else
        check_error "PySide6 non installé (pip install PySide6)"
    fi

    # sounddevice
    if $PYTHON_EXE -c "import sounddevice" 2>/dev/null; then
        check_ok "sounddevice installé"
    else
        check_error "sounddevice non installé (pip install sounddevice)"
    fi

    # pyperclip
    if $PYTHON_EXE -c "import pyperclip" 2>/dev/null; then
        check_ok "pyperclip installé"
    else
        check_error "pyperclip non installé (pip install pyperclip)"
    fi

    # pynput
    if $PYTHON_EXE -c "import pynput" 2>/dev/null; then
        check_ok "pynput installé"
    else
        check_error "pynput non installé (pip install pynput)"
    fi
else
    check_warn "Impossible de tester les dépendances Python (venv non trouvé)"
fi
echo ""

# 5. Vérifier xdotool
echo "[5/10] Vérification de xdotool (collage Linux)..."
if command -v xdotool &> /dev/null; then
    XDOTOOL_VERSION=$(xdotool version 2>&1 | head -n1)
    check_ok "xdotool installé: $XDOTOOL_VERSION"
else
    check_error "xdotool non installé (sudo apt install xdotool)"
fi
echo ""

# 6. Vérifier xclip/xsel
echo "[6/10] Vérification du presse-papiers..."
if command -v xclip &> /dev/null; then
    check_ok "xclip installé"
elif command -v xsel &> /dev/null; then
    check_ok "xsel installé"
else
    check_error "xclip/xsel non installé (sudo apt install xclip xsel)"
fi
echo ""

# 7. Vérifier PortAudio
echo "[7/10] Vérification de PortAudio (audio)..."
if ldconfig -p 2>/dev/null | grep -q libportaudio; then
    check_ok "PortAudio installé"
else
    check_warn "PortAudio non détecté (sudo apt install portaudio19-dev)"
fi
echo ""

# 8. Vérifier l'environnement graphique
echo "[8/10] Vérification de l'environnement graphique..."
if [ -n "$DISPLAY" ]; then
    check_ok "X11 détecté (DISPLAY=$DISPLAY)"
elif [ -n "$WAYLAND_DISPLAY" ]; then
    check_ok "Wayland détecté (WAYLAND_DISPLAY=$WAYLAND_DISPLAY)"
    check_warn "Note: xdotool peut ne pas fonctionner sous Wayland"
else
    check_error "Aucun environnement graphique détecté"
fi
echo ""

# 9. Vérifier les périphériques audio
echo "[9/10] Vérification des périphériques audio..."
if command -v python3 &> /dev/null && [ -f ".venv/bin/python" -o -f ".venv/bin/python3" ]; then
    AUDIO_DEVICES=$($PYTHON_EXE -c "import sounddevice as sd; devs = sd.query_devices(); input_devs = [d for d in devs if d['max_input_channels'] > 0]; print(len(input_devs))" 2>/dev/null)

    if [ -n "$AUDIO_DEVICES" ] && [ "$AUDIO_DEVICES" -gt 0 ]; then
        check_ok "Périphériques d'entrée audio détectés: $AUDIO_DEVICES"
        echo "    Liste des micros:"
        $PYTHON_EXE -c "import sounddevice as sd; devs = sd.query_devices(); [print(f'      [{i}] {d[\"name\"]}') for i, d in enumerate(devs) if d['max_input_channels'] > 0]" 2>/dev/null
    else
        check_error "Aucun périphérique d'entrée audio détecté"
    fi
else
    check_warn "Impossible de tester les périphériques audio"
fi
echo ""

# 10. Vérifier la structure du projet
echo "[10/10] Vérification de la structure du projet..."
if [ -f "main.py" ]; then
    check_ok "main.py trouvé"
else
    check_error "main.py non trouvé"
fi

if [ -d "core" ]; then
    check_ok "Module core/ trouvé"
else
    check_error "Module core/ non trouvé"
fi

if [ -d "ui" ]; then
    check_ok "Module ui/ trouvé"
else
    check_error "Module ui/ non trouvé"
fi

if [ -d "api" ]; then
    check_ok "Module api/ trouvé"
else
    check_error "Module api/ non trouvé"
fi

if [ -f "scripts/start_transcription.sh" ] && [ -x "scripts/start_transcription.sh" ]; then
    check_ok "Scripts shell trouvés et exécutables"
else
    check_error "Scripts shell manquants ou non exécutables"
    echo "    Correction: chmod +x scripts/*.sh"
fi
echo ""

# Résumé
echo "================================================"
echo "RÉSUMÉ DU TEST"
echo "================================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✓ Tous les tests ont réussi!"
    echo ""
    echo "Vous pouvez lancer l'application avec:"
    echo "  bash scripts/start_transcription.sh        (mode normal)"
    echo "  bash scripts/start_transcription_debug.sh  (mode debug)"
    EXIT_CODE=0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠ Tests réussis avec $WARNINGS avertissement(s)"
    echo ""
    echo "Vous pouvez essayer de lancer l'application, mais certaines"
    echo "fonctionnalités peuvent ne pas fonctionner correctement."
    EXIT_CODE=0
else
    echo "✗ $ERRORS erreur(s) détectée(s), $WARNINGS avertissement(s)"
    echo ""
    echo "Veuillez corriger les erreurs avant de lancer l'application."
    echo "Consultez docs/INSTALL_UBUNTU.md pour plus d'informations."
    EXIT_CODE=1
fi
echo ""

exit $EXIT_CODE
