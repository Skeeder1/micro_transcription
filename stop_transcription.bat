@echo off
REM Script d'arret pour le systeme de transcription
REM Ferme tous les processus Python et visualizer associes

echo ================================================
echo Arret du Systeme de Dictee Vocale
echo ================================================
echo.

echo [INFO] Arret des processus Python...

REM Tuer tous les processus python.exe du venv
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq Systeme de Dictee Vocale Avance*" 2>nul
if %errorlevel% equ 0 (
    echo   - Processus principal arrete
) else (
    echo   - Aucun processus principal trouve
)

REM Tuer tous les processus pythonw.exe (daemon en arriere-plan)
taskkill /F /IM pythonw.exe 2>nul
if %errorlevel% equ 0 (
    echo   - Daemon Python arrete
) else (
    echo   - Aucun daemon Python trouve
)

REM Tuer le processus mic_visualizer_enhanced.py
echo.
echo [INFO] Arret du visualizer...
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *mic_visualizer*" 2>nul
taskkill /F /FI "IMAGENAME eq pythonw.exe" /FI "COMMANDLINE eq *mic_visualizer_enhanced.py*" 2>nul

REM Verifier si des processus Python liés au projet sont encore actifs
echo.
echo [INFO] Verification des processus restants...
set "found=0"
for /f "tokens=*" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>nul ^| find "python.exe"') do set "found=1"
for /f "tokens=*" %%a in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO CSV /NH 2^>nul ^| find "pythonw.exe"') do set "found=1"

if %found% equ 1 (
    echo   [WARN] Certains processus Python sont encore actifs
    echo   - Arret de tous les processus Python...
    taskkill /F /IM python.exe 2>nul
    taskkill /F /IM pythonw.exe 2>nul
    echo   - Tous les processus Python arretes
) else (
    echo   - Aucun processus Python restant
)

echo.
echo ================================================
echo Arret termine
echo ================================================
