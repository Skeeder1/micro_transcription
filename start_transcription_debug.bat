@echo off
REM Script de lancement en mode DEBUG pour main_enhanced.py avec venv
REM Terminal visible pour voir les messages de debug et les erreurs

echo ================================================
echo Systeme de Dictee Vocale Avance - MODE DEBUG
echo ================================================
echo.

REM Arreter toute instance precedente
echo [INFO] Arret des instances precedentes...
call stop_transcription.bat >nul 2>&1
timeout /t 1 /nobreak >nul
echo.

REM Verifier que le venv existe
if not exist ".venv\Scripts\python.exe" (
    echo ERREUR: Virtual environment introuvable!
    echo Verifiez que .venv existe dans ce dossier.
    pause
    exit /b 1
)

REM Afficher quelle version de Python est utilisee
echo [INFO] Utilisation du venv Python:
.venv\Scripts\python.exe --version
echo.

REM Verifier Flask
echo [INFO] Verification de Flask...
.venv\Scripts\python.exe -c "from flask import Flask; print('Flask OK')" 2>nul
if errorlevel 1 (
    echo [WARN] Flask non installe. Installation en cours...
    .venv\Scripts\python.exe -m pip install flask
)

echo.
echo [INFO] Lancement de main_enhanced.py en MODE DEBUG...
echo [INFO] Le terminal reste ouvert pour afficher les logs
echo [INFO] Appuyez sur Ctrl+C pour arreter l'application
echo.

REM Lancer main_enhanced.py avec python.exe (pas pythonw.exe) pour voir la console
.venv\Scripts\python.exe main_enhanced.py

echo.
echo ================================================
echo Application arretee
echo ================================================
pause
