@echo off@echo off@echo off

REM ================================================

REM   Application de Transcription VocaleREM ================================================REM Script de lancement pour main_enhanced.py avec venv

REM ================================================

REM   Application de Transcription VocaleREM Garantit l'utilisation du bon environnement Python

echo.

echo ================================================REM ================================================

echo   Application de Transcription Vocale

echo ================================================echo ================================================

echo.

echo.echo Systeme de Dictee Vocale Avance

REM Verifier que le venv existe

if not exist ".venv\Scripts\python.exe" (echo ================================================echo ================================================

    echo [ERREUR] Virtual environment introuvable!

    echo Verifiez que .venv existe dans ce dossier.echo   Application de Transcription Vocaleecho.

    echo.

    pauseecho ================================================

    exit /b 1

)echo.REM Arreter toute instance precedente



REM Afficher version Pythonecho [INFO] Arret des instances precedentes...

echo [INFO] Utilisation du venv Python:

.venv\Scripts\python.exe --versionREM Verifier que le venv existecall stop_transcription.bat >nul 2>&1

echo.

if not exist ".venv\Scripts\python.exe" (timeout /t 1 /nobreak >nul

REM Nettoyer les instances existantes de transcription

echo [INFO] Fermeture des applications de transcription existantes...    echo [ERREUR] Virtual environment introuvable!echo.

taskkill /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *main_enhanced.py*" /F >nul 2>&1

timeout /t 1 /nobreak >nul    echo Verifiez que .venv existe dans ce dossier.

echo [INFO] Nettoyage termine.

echo.    echo.REM Verifier que le venv existe



REM Verifier les dependances    pauseif not exist ".venv\Scripts\python.exe" (

echo [INFO] Verification des dependances...

.venv\Scripts\python.exe -c "import torch; import faster_whisper; import pyautogui" 2>nul    exit /b 1    echo ERREUR: Virtual environment introuvable!

if errorlevel 1 (

    echo [WARN] Certaines dependances manquent.)    echo Verifiez que .venv existe dans ce dossier.

    echo        Verifiez l'installation avec: pip install -r requirements.txt

    echo.    pause

    pause

)REM Afficher version Python    exit /b 1

echo.

echo [INFO] Utilisation du venv Python:)

echo ================================================

echo   Lancement de la Transcription.venv\Scripts\python.exe --version

echo ================================================

echo.echo.REM Afficher quelle version de Python est utilisee

echo [INFO] Commandes:

echo        F9        : Basculer veille/actifecho [INFO] Utilisation du venv Python:

echo        Ctrl+C    : Arreter l'application

echo.REM Verifier les dependances.venv\Scripts\python.exe --version

echo [INFO] Demarrage...

echo.echo [INFO] Verification des dependances...echo.



.venv\Scripts\python.exe main_enhanced.py.venv\Scripts\python.exe -c "import torch; import faster_whisper; import pyautogui" 2>nul



echo.if errorlevel 1 (REM Verifier Flask

echo [INFO] Application de transcription arretee.

pause    echo [WARN] Certaines dependances manquent.echo [INFO] Verification de Flask...


    echo        Verifiez l'installation avec: pip install -r requirements.txt.venv\Scripts\python.exe -c "from flask import Flask; print('Flask OK')" 2>nul

    echo.if errorlevel 1 (

    pause    echo [WARN] Flask non installe. Installation en cours...

)    .venv\Scripts\python.exe -m pip install flask

echo.)



echo ================================================echo.

echo   Lancement de la Transcriptionecho [INFO] Lancement de main_enhanced.py en mode daemon...

echo ================================================echo.

echo.

echo [INFO] Commandes:REM Lancer main_enhanced.py en mode daemon (terminal masque)

echo        F9        : Basculer veille/actifstart "" /B .venv\Scripts\pythonw.exe main_enhanced.py

echo        Ctrl+C    : Arreter l'application

echo.echo.

echo [INFO] Demarrage...echo ================================================

echo.echo Daemon demarre en arriere-plan

echo ================================================

.venv\Scripts\python.exe main_enhanced.pytimeout /t 2 /nobreak >nul


echo.
echo [INFO] Application de transcription arretee.
pause
