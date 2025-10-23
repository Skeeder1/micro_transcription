@echo off
REM ================================================
REM   Arreter toutes les instances du systeme
REM ================================================

echo.
echo ================================================
echo   Arret du Systeme de Dictee Vocale
echo ================================================
echo.

echo [INFO] Fermeture de toutes les instances...
echo.

REM Arreter le visualiseur
echo [1/2] Arret du visualiseur...
taskkill /FI "IMAGENAME eq pythonw.exe" /FI "WINDOWTITLE eq *visualizer*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Visualiseur Audio*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Micro Monitor*" /F >nul 2>&1
timeout /t 1 /nobreak >nul
echo       Visualiseur arrete.

REM Arreter la transcription
echo [2/2] Arret de l'application de transcription...
taskkill /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *main_enhanced.py*" /F >nul 2>&1
timeout /t 1 /nobreak >nul
echo       Transcription arretee.

echo.
echo ================================================
echo   Systeme arrete avec succes
echo ================================================
echo.
pause
