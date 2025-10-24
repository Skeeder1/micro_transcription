@echo off
REM Script de lancement en mode DEBUG pour le systeme de transcription v2.0
REM Terminal visible pour voir les logs detailles et diagnostiquer les problemes

echo ================================================
echo Systeme de Dictee Vocale Avance v2.0
echo MODE DEBUG - Console Visible
echo ================================================
echo.

REM Changer vers le repertoire du projet
cd /d "%~dp0\.."

REM Arreter toute instance precedente
echo [ETAPE 1/5] Arret des instances precedentes...
call "%~dp0stop_transcription.bat" >nul 2>&1
timeout /t 1 /nobreak >nul
echo   [OK] Instances precedentes arretees
echo.

REM Verifier que le venv existe
echo [ETAPE 2/5] Verification de l'environnement...
if not exist ".venv\Scripts\python.exe" (
    echo   [ERREUR] Virtual environment introuvable!
    echo   Verifiez que .venv existe dans: %CD%
    echo.
    pause
    exit /b 1
)

REM Afficher quelle version de Python est utilisee
.venv\Scripts\python.exe --version
echo   [OK] Environnement virtuel trouve
echo.

REM Verifier les dependances critiques
echo [ETAPE 3/5] Verification des dependances...
.venv\Scripts\python.exe -c "import flask" 2>nul
if errorlevel 1 (
    echo   [WARN] Flask non installe. Installation en cours...
    .venv\Scripts\python.exe -m pip install flask
)

.venv\Scripts\python.exe -c "import faster_whisper" 2>nul
if errorlevel 1 (
    echo   [ERREUR] faster-whisper non installe!
    echo   Installez les dependances avec: pip install -r requirements.txt
    pause
    exit /b 1
)

.venv\Scripts\python.exe -c "import PySide6" 2>nul
if errorlevel 1 (
    echo   [ERREUR] PySide6 non installe!
    echo   Installez les dependances avec: pip install -r requirements.txt
    pause
    exit /b 1
)

.venv\Scripts\python.exe -c "import sounddevice" 2>nul
if errorlevel 1 (
    echo   [ERREUR] sounddevice non installe!
    echo   Installez les dependances avec: pip install -r requirements.txt
    pause
    exit /b 1
)

echo   [OK] Flask - OK
echo   [OK] faster-whisper - OK
echo   [OK] PySide6 - OK
echo   [OK] sounddevice - OK
echo.

REM Verifier la structure du projet
echo [ETAPE 4/5] Verification de la structure du projet...
if not exist "main.py" (
    echo   [ERREUR] main.py introuvable!
    echo   Verifiez que vous etes dans le bon repertoire.
    pause
    exit /b 1
)

if not exist "core" (
    echo   [ERREUR] Module core/ introuvable!
    pause
    exit /b 1
)

if not exist "ui" (
    echo   [ERREUR] Module ui/ introuvable!
    pause
    exit /b 1
)

if not exist "api" (
    echo   [ERREUR] Module api/ introuvable!
    pause
    exit /b 1
)

echo   [OK] main.py - OK
echo   [OK] Module core/ - OK
echo   [OK] Module ui/ - OK
echo   [OK] Module api/ - OK
echo   [OK] Module shared/ - OK
echo.

REM Lancer l'application en mode DEBUG
echo [ETAPE 5/5] Demarrage du systeme en MODE DEBUG...
echo.
echo ================================================
echo INFORMATIONS MODE DEBUG
echo ================================================
echo.
echo Ce mode affiche tous les logs en temps reel:
echo   - Messages du module CORE (transcription)
echo   - Messages du module API (serveur Flask)
echo   - Messages du module UI (visualiseur)
echo   - Erreurs et warnings detailles
echo.
echo La console reste ouverte pour diagnostiquer les problemes.
echo.
echo Appuyez sur Ctrl+C pour arreter l'application.
echo ================================================
echo.
timeout /t 2 /nobreak >nul

REM Lancer main.py avec python.exe (pas pythonw.exe) pour voir la console
.venv\Scripts\python.exe main.py

echo.
echo ================================================
echo Application arretee
echo ================================================
pause
