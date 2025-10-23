@echo off
REM ================================================
REM   Systeme de Dictee Vocale - Demarrage Complet
REM ================================================

echo.
echo ================================================
echo   Systeme de Dictee Vocale Avance
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

REM Verifier et installer les dependances du visualiseur
echo [INFO] Verification des dependances...
.venv\Scripts\python.exe -c "from flask_cors import CORS; print('Dependances OK')" 2>nul
if errorlevel 1 (
    echo [WARN] Dependances manquantes. Installation en cours...
    .venv\Scripts\python.exe -m pip install -q -r visualizer/requirements.txt
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation des dependances
        pause
        exit /b 1
    )
    echo [INFO] Dependances installees avec succes
)
echo.

echo ================================================
echo   Demarrage du systeme
echo ================================================
echo.
echo [INFO] Lancement du visualiseur web...
echo        Interface: http://127.0.0.1:5500
echo.

REM Lancer le visualiseur en arriere-plan
start "Visualiseur Audio" /MIN .venv\Scripts\python.exe run_visualizer.py

REM Attendre que le serveur demarre
timeout /t 3 /nobreak >nul

REM Ouvrir le navigateur
echo [INFO] Ouverture du navigateur...
start http://127.0.0.1:5500
echo.

REM Lancer l'application de transcription au premier plan
echo [INFO] Lancement de l'application de transcription...
echo        Appuyez sur F9 pour basculer veille/actif
echo        Appuyez sur Ctrl+C pour arreter
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

echo.
echo Systeme arrete.
pause
