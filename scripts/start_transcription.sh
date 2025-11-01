#!/bin/bash
# Script de lancement pour le systeme de transcription v2.0
# Demarre tous les modules: Core, UI, API

echo "================================================"
echo "Systeme de Dictee Vocale Avance v2.0"
echo "================================================"
echo ""

# Changer vers le repertoire du projet
cd "$(dirname "$0")/.." || exit 1

# Arreter toute instance precedente
echo "[ETAPE 1/5] Arret des instances precedentes..."
echo "   [INFO] Appel du script stop_transcription.sh..."
bash "$(dirname "$0")/stop_transcription.sh" >/dev/null 2>&1
sleep 2
echo "   [OK] Instances precedentes arretees"
echo ""

# Verifier que le venv existe
echo "[ETAPE 2/5] Verification de l'environnement..."
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
echo "[ETAPE 3/5] Verification des dependances..."
$PYTHON_EXE -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   [WARN] Flask non installe. Installation en cours..."
    $PYTHON_EXE -m pip install flask >/dev/null 2>&1
fi

$PYTHON_EXE -c "import faster_whisper" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   [WARN] faster-whisper non installe!"
    echo "   Installez les dependances avec: pip install -r requirements.txt"
    read -p "Appuyez sur Entree pour continuer..."
    exit 1
fi

$PYTHON_EXE -c "import PySide6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   [WARN] PySide6 non installe!"
    echo "   Installez les dependances avec: pip install -r requirements.txt"
    read -p "Appuyez sur Entree pour continuer..."
    exit 1
fi

# Verifier les dependances systeme Ubuntu
if [ "$(uname)" = "Linux" ]; then
    if ! command -v xdotool &> /dev/null; then
        echo "   [WARN] xdotool non installe (requis pour le collage sous Linux)"
        echo "   Installez avec: sudo apt install xdotool"
    fi

    if ! command -v xclip &> /dev/null && ! command -v xsel &> /dev/null; then
        echo "   [WARN] xclip/xsel non installe (requis pour le presse-papiers)"
        echo "   Installez avec: sudo apt install xclip xsel"
    fi
fi

echo "   [OK] Flask - OK"
echo "   [OK] faster-whisper - OK"
echo "   [OK] PySide6 - OK"
echo ""

# Verifier la structure du projet
echo "[ETAPE 4/5] Verification de la structure du projet..."
if [ ! -f "main.py" ]; then
    echo "   [ERREUR] main.py introuvable!"
    echo "   Verifiez que vous etes dans le bon repertoire."
    read -p "Appuyez sur Entree pour continuer..."
    exit 1
fi

if [ ! -d "core" ]; then
    echo "   [ERREUR] Module core/ introuvable!"
    read -p "Appuyez sur Entree pour continuer..."
    exit 1
fi

if [ ! -d "ui" ]; then
    echo "   [ERREUR] Module ui/ introuvable!"
    read -p "Appuyez sur Entree pour continuer..."
    exit 1
fi

if [ ! -d "api" ]; then
    echo "   [ERREUR] Module api/ introuvable!"
    read -p "Appuyez sur Entree pour continuer..."
    exit 1
fi

echo "   [OK] main.py - OK"
echo "   [OK] Module core/ - OK"
echo "   [OK] Module ui/ - OK"
echo "   [OK] Module api/ - OK"
echo ""

# Lancer l'application
echo "[ETAPE 5/5] Demarrage du systeme..."
echo ""
echo "   Modules demarre:"
echo "   [1/3] Core (transcription Whisper)"
echo "   [2/3] API (serveur Flask SSE)"
echo "   [3/3] UI (visualiseur Qt6)"
echo ""
echo "   NOTE: Mode arriere-plan - Hotkey F9 peut ne pas fonctionner"
echo "   Pour utiliser F9, lancez: ./start_foreground.sh"
echo ""

# Sur Linux, lancer en arriere-plan avec nohup
# AVERTISSEMENT: Le mode arriere-plan peut ne pas supporter les hotkeys (F9)
# Pour hotkeys: utilisez ./start_foreground.sh
nohup $PYTHON_EXE main.py > /tmp/transcription_$(date +%Y%m%d_%H%M%S).log 2>&1 &

echo "   [OK] Systeme demarre en arriere-plan (PID: $!)"
echo ""
sleep 2

echo "================================================"
echo "Systeme demarre avec succes!"
echo "================================================"
echo ""
echo "Fonctionnalites:"
echo "   - Transcription temps reel (Whisper)"
echo "   - Visualiseur d'ondes audio"
echo "   - Hotkey F9: Veille/Actif"
echo "   - Auto-veille apres 10s d'inactivite"
echo ""
echo "Pour arreter: scripts/stop_transcription.sh"
echo "Pour debug:   scripts/start_transcription_debug.sh"
echo ""
echo "Logs disponibles dans: /tmp/transcription_*.log"
echo ""
sleep 3
