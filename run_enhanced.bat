@echo off
REM Script de lancement pour main_enhanced.py avec venv
REM Garantit l'utilisation du bon environnement Python

echo ================================================
echo Systeme de Dictee Vocale Avance
echo ================================================
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
echo [INFO] Lancement de main_enhanced.py...
echo.

REM Lancer main_enhanced.py
.venv\Scripts\python.exe main_enhanced.py

echo.
echo ================================================
echo Programme termine
echo ================================================
pause
