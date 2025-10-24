@echo off
REM Script d'arret pour le systeme de transcription v2.0
REM Ferme tous les processus Python et modules associes (core, ui, api)

echo ================================================
echo Arret du Systeme de Dictee Vocale v2.0
echo ================================================
echo.

REM Changer vers le repertoire du projet
cd /d "%~dp0\.."

echo [INFO] Arret des modules du projet...
echo.

REM Tuer le processus principal (main.py)
echo [1/3] Arret du module CORE (main.py)...
taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *main.py*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Module CORE arrete
) else (
    echo   [INFO] Module CORE non trouve
)

taskkill /F /FI "IMAGENAME eq pythonw.exe" /FI "COMMANDLINE eq *main.py*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Daemon CORE arrete
)

echo.
echo [2/3] Arret du module UI (visualizer)...
REM Tuer le processus visualizer (ui.visualizer_app ou ui module)
taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *ui.visualizer_app*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Module UI arrete
) else (
    echo   [INFO] Module UI non trouve
)

taskkill /F /FI "IMAGENAME eq pythonw.exe" /FI "COMMANDLINE eq *ui.visualizer_app*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Daemon UI arrete
)

taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *-m ui*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Module UI (via -m) arrete
)

taskkill /F /FI "IMAGENAME eq pythonw.exe" /FI "COMMANDLINE eq *-m ui*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Daemon UI (via -m) arrete
)

echo.
echo [3/3] Arret du module API (Flask)...
REM Tuer les processus Flask/Werkzeug (api.server)
taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *api.server*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Module API arrete
) else (
    echo   [INFO] Module API non trouve
)

taskkill /F /FI "IMAGENAME eq pythonw.exe" /FI "COMMANDLINE eq *api.server*" 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Daemon API arrete
)

echo.
echo [INFO] Verification finale des processus restants...

REM Verifier si des processus Python du projet sont encore actifs
set "found=0"
for /f "tokens=*" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>nul ^| find "python.exe" ^| find /i "transcription-audio"') do set "found=1"
for /f "tokens=*" %%a in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO CSV /NH 2^>nul ^| find "pythonw.exe" ^| find /i "transcription-audio"') do set "found=1"

if %found% equ 1 (
    echo   [WARN] Certains processus du projet sont encore actifs
    echo   [ACTION] Tentative d'arret force...

    REM Tuer tous les processus pythonw.exe dans le dossier du projet
    for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO CSV /NH 2^>nul ^| find "pythonw.exe"') do (
        taskkill /F /PID %%p 2>nul
    )

    echo   [OK] Nettoyage force termine
) else (
    echo   [OK] Aucun processus du projet restant
)

echo.
echo ================================================
echo Arret termine - Tous les modules arretes
echo ================================================
echo.
echo Modules arretes:
echo   - Core (transcription)
echo   - UI (visualizer)
echo   - API (serveur Flask)
echo.
timeout /t 2 /nobreak >nul
