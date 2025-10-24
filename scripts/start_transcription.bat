@echo off
REM Script de lancement pour le systeme de transcription v2.0
REM Demarre tous les modules: Core, UI, API

echo ================================================
echo Systeme de Dictee Vocale Avance v2.0
echo ================================================
echo.

REM Changer vers le repertoire du projet
cd /d "%~dp0\.."

REM Arreter toute instance precedente
echo [ETAPE 1/5] Arret des instances precedentes...
echo   [INFO] Appel du script stop_transcription.bat...
call "%~dp0stop_transcription.bat" >nul 2>&1
timeout /t 2 /nobreak >nul
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
    .venv\Scripts\python.exe -m pip install flask >nul 2>&1
)

.venv\Scripts\python.exe -c "import faster_whisper" 2>nul
if errorlevel 1 (
    echo   [WARN] faster-whisper non installe!
    echo   Installez les dependances avec: pip install -r requirements.txt
    pause
    exit /b 1
)

.venv\Scripts\python.exe -c "import PySide6" 2>nul
if errorlevel 1 (
    echo   [WARN] PySide6 non installe!
    echo   Installez les dependances avec: pip install -r requirements.txt
    pause
    exit /b 1
)

echo   [OK] Flask - OK
echo   [OK] faster-whisper - OK
echo   [OK] PySide6 - OK
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
echo.

REM Lancer l'application
echo [ETAPE 5/5] Demarrage du systeme...
echo.
echo   Modules demarre:
echo   [1/3] Core (transcription Whisper)
echo   [2/3] API (serveur Flask SSE)
echo   [3/3] UI (visualiseur Qt6)
echo.

start "" /B .venv\Scripts\pythonw.exe main.py

echo   [OK] Systeme demarre en arriere-plan
echo.
timeout /t 2 /nobreak >nul

echo ================================================
echo Systeme demarre avec succes!
echo ================================================
echo.
echo Fonctionnalites:
echo   - Transcription temps reel (Whisper)
echo   - Visualiseur d'ondes audio
echo   - Hotkey F9: Veille/Actif
echo   - Auto-veille apres 10s d'inactivite
echo.
echo Pour arreter: scripts\stop_transcription.bat
echo Pour debug:   scripts\start_transcription_debug.bat
echo.
timeout /t 3 /nobreak >nul
