@echo off
REM ================================================
REM   Systeme de Dictee Vocale - Demarrage Complet
REM ================================================

echo.
echo ================================================
echo   Systeme de Dictee Vocale Avance
echo   (Visualiseur + Transcription)
echo ================================================
echo.

REM Verifier que le venv existe
if not exist ".venv\Scripts\python.exe" (
    echo [ERREUR] Virtual environment introuvable!
    echo Verifiez que .venv existe dans ce dossier.
    echo.
    pause
    exit /b 1
)

REM Afficher version Python
echo [INFO] Utilisation du venv Python:
.venv\Scripts\python.exe --version
echo.

REM Nettoyer les instances existantes
echo [INFO] Nettoyage des instances existantes...
taskkill /FI "IMAGENAME eq pythonw.exe" /FI "WINDOWTITLE eq *visualizer*" /F >nul 2>&1
taskkill /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *main_enhanced.py*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Visualiseur Audio*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Micro Monitor*" /F >nul 2>&1
timeout /t 1 /nobreak >nul
echo [INFO] Nettoyage termine.
echo.

REM Verifier PySide6
echo [INFO] Verification de PySide6...
.venv\Scripts\python.exe -c "import PySide6" 2>nul
if errorlevel 1 (
    echo [WARN] PySide6 manquant. Installation en cours...
    .venv\Scripts\python.exe -m pip install -q PySide6 PySide6-WebEngine
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation de PySide6
        pause
        exit /b 1
    )
    echo [INFO] PySide6 installe avec succes
)
echo.

echo ================================================
echo   Demarrage du systeme complet
echo ================================================
echo.
echo [INFO] 1/2 - Lancement du visualiseur (fenetre native)...
echo        - Fenetre toujours au premier plan
echo        - Masquage automatique en mode veille (F9)
echo.

REM Lancer le visualiseur en arriere-plan
start "Visualiseur Audio" /MIN .venv\Scripts\pythonw.exe visualizer_window.py

REM Attendre que la fenetre se charge
timeout /t 2 /nobreak >nul
echo [INFO] Visualiseur demarre.
echo.

REM Lancer l'application de transcription au premier plan
echo [INFO] 2/2 - Lancement de l'application de transcription...
echo.
echo        Commandes:
echo        F9        : Basculer veille/actif
echo        Ctrl+C    : Arreter le systeme
echo.
echo ================================================
echo.

.venv\Scripts\python.exe main_enhanced.py

REM Nettoyer a la sortie
echo.
echo ================================================
echo   Arret du systeme
echo ================================================
echo.
echo [INFO] Arret du visualiseur...
taskkill /FI "WINDOWTITLE eq Visualiseur Audio*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Micro Monitor*" /F >nul 2>&1

echo.
echo [INFO] Systeme arrete.
pause
