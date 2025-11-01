#!/bin/bash
# Script de lancement DEBUG pour le systeme de transcription v2.0
# Affiche tous les logs dans le terminal (pas d'arriere-plan)

echo "================================================"
echo "Systeme de Dictee Vocale Avance v2.0 - DEBUG"
echo "================================================"
echo ""

# Changer vers le repertoire du projet
cd "$(dirname "$0")/.." || exit 1

# Arreter toute instance precedente
echo "[ETAPE 1/6] Arret des instances precedentes..."
echo "   [INFO] Appel du script stop_transcription.sh..."
bash "$(dirname "$0")/stop_transcription.sh" >/dev/null 2>&1
sleep 2
echo "   [OK] Instances precedentes arretees"
echo ""

# Verifier que le venv existe
echo "[ETAPE 2/6] Verification de l'environnement..."
if [ ! -f ".venv/bin/python" ] && [ ! -f ".venv/bin/python3" ]; then
    echo "   [ERREUR] Virtual environment introuvable!"
    echo "   Verifiez que .venv existe dans: $(pwd)"
    echo ""
    read -p "Appuyez sur Entree pour continuer..."
    exit 1
fi

# Determiner l'executable Python
if [ -f ".venv/bin/python3" ]; then
    PYTHON_EXE=".venv/bin/python3"
else
    PYTHON_EXE=".venv/bin/python"
fi

# Afficher quelle version de Python est utilisee
$PYTHON_EXE --version
echo "   [OK] Environnement virtuel trouve"
echo ""

# Verifier les dependances critiques
echo "[ETAPE 3/6] Verification des dependances Python..."
$PYTHON_EXE -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   [ERREUR] Flask non installe!"
    exit 1
fi

$PYTHON_EXE -c "import faster_whisper" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   [ERREUR] faster-whisper non installe!"
    exit 1
fi

$PYTHON_EXE -c "import PySide6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   [ERREUR] PySide6 non installe!"
    exit 1
fi

$PYTHON_EXE -c "import sounddevice" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   [ERREUR] sounddevice non installe!"
    exit 1
fi

echo "   [OK] Flask - OK"
echo "   [OK] faster-whisper - OK"
echo "   [OK] PySide6 - OK"
echo "   [OK] sounddevice - OK"
echo ""

# Verifier les dependances systeme Ubuntu
echo "[ETAPE 4/6] Verification des dependances systeme Ubuntu..."
if [ "$(uname)" = "Linux" ]; then
    # Verifier xdotool pour le collage
    if command -v xdotool &> /dev/null; then
        echo "   [OK] xdotool - OK (requis pour collage)"
    else
        echo "   [WARN] xdotool NON INSTALLE"
        echo "          Installation: sudo apt install xdotool"
    fi

    # Verifier xclip/xsel pour le presse-papiers
    if command -v xclip &> /dev/null; then
        echo "   [OK] xclip - OK (requis pour presse-papiers)"
    elif command -v xsel &> /dev/null; then
        echo "   [OK] xsel - OK (requis pour presse-papiers)"
    else
        echo "   [WARN] xclip/xsel NON INSTALLE"
        echo "          Installation: sudo apt install xclip xsel"
    fi

    # Verifier portaudio pour sounddevice
    if ldconfig -p | grep -q libportaudio; then
        echo "   [OK] portaudio19 - OK (requis pour audio)"
    else
        echo "   [WARN] portaudio19 NON INSTALLE"
        echo "          Installation: sudo apt install portaudio19-dev"
    fi

    # Detecter l'environnement graphique
    if [ -n "$WAYLAND_DISPLAY" ]; then
        echo "   [INFO] Environnement detecte: WAYLAND"
        echo "          Note: xdotool peut ne pas fonctionner sous Wayland"
        echo "          Installez ydotool si necessaire: sudo apt install ydotool"
    elif [ -n "$DISPLAY" ]; then
        echo "   [INFO] Environnement detecte: X11"
    else
        echo "   [WARN] Aucun environnement graphique detecte!"
    fi
fi
echo ""

# Verifier la structure du projet
echo "[ETAPE 5/6] Verification de la structure du projet..."
if [ ! -f "main.py" ]; then
    echo "   [ERREUR] main.py introuvable!"
    exit 1
fi

if [ ! -d "core" ]; then
    echo "   [ERREUR] Module core/ introuvable!"
    exit 1
fi

if [ ! -d "ui" ]; then
    echo "   [ERREUR] Module ui/ introuvable!"
    exit 1
fi

if [ ! -d "api" ]; then
    echo "   [ERREUR] Module api/ introuvable!"
    exit 1
fi

echo "   [OK] main.py - OK"
echo "   [OK] Module core/ - OK"
echo "   [OK] Module ui/ - OK"
echo "   [OK] Module api/ - OK"
echo ""

# Lancer l'application en mode DEBUG (foreground)
echo "[ETAPE 6/6] Demarrage du systeme en MODE DEBUG..."
echo ""
echo "   ATTENTION: Le terminal va afficher tous les logs"
echo "   Appuyez sur Ctrl+C pour arreter"
echo ""
echo "================================================"
echo "DEMARRAGE..."
echo "================================================"
echo ""
sleep 2

# Lancer au premier plan pour voir tous les logs
exec $PYTHON_EXE main.py
