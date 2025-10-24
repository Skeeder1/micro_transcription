@echo off
setlocal EnableDelayedExpansion
REM Script d'arret pour le systeme de transcription v2.0
REM Ferme tous les processus Python et modules associes (core, ui, api)
REM Protection: ne tue pas le processus appelant

echo ================================================
echo Arret du Systeme de Dictee Vocale v2.0
echo ================================================
echo.

REM Changer vers le repertoire du projet
cd /d "%~dp0\.."

echo [INFO] Arret des modules du projet...
echo   [Protection activee: processus appelant preserve]
echo.

REM Tuer le processus principal (main.py) - exclure cmd.exe et batch scripts
echo [1/3] Arret du module CORE (main.py)...

REM Cibler uniquement les processus Python executant main.py
for /f "tokens=2" %%p in ('wmic process where "name='python.exe' and CommandLine like '%%main.py%%'" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    set "pid=%%p"
    echo   [INFO] Arret processus CORE PID: !pid!
    taskkill /F /PID !pid! >nul 2>&1
)

for /f "tokens=2" %%p in ('wmic process where "name='pythonw.exe' and CommandLine like '%%main.py%%'" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    set "pid=%%p"
    echo   [INFO] Arret daemon CORE PID: !pid!
    taskkill /F /PID !pid! >nul 2>&1
)

echo   [OK] Module CORE arrete

echo.
echo [2/3] Arret du module UI (visualizer)...

REM Tuer les processus UI
for /f "tokens=2" %%p in ('wmic process where "name='python.exe' and (CommandLine like '%%ui.visualizer_app%%' or CommandLine like '%%-m ui%%')" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    set "pid=%%p"
    echo   [INFO] Arret processus UI PID: !pid!
    taskkill /F /PID !pid! >nul 2>&1
)

for /f "tokens=2" %%p in ('wmic process where "name='pythonw.exe' and (CommandLine like '%%ui.visualizer_app%%' or CommandLine like '%%-m ui%%')" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    set "pid=%%p"
    echo   [INFO] Arret daemon UI PID: !pid!
    taskkill /F /PID !pid! >nul 2>&1
)

echo   [OK] Module UI arrete

echo.
echo [3/3] Arret du module API (Flask)...

REM Tuer les processus Flask/Werkzeug (api.server)
for /f "tokens=2" %%p in ('wmic process where "name='python.exe' and CommandLine like '%%api.server%%'" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    set "pid=%%p"
    echo   [INFO] Arret processus API PID: !pid!
    taskkill /F /PID !pid! >nul 2>&1
)

for /f "tokens=2" %%p in ('wmic process where "name='pythonw.exe' and CommandLine like '%%api.server%%'" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    set "pid=%%p"
    echo   [INFO] Arret daemon API PID: !pid!
    taskkill /F /PID !pid! >nul 2>&1
)

echo   [OK] Module API arrete

echo.
echo [INFO] Verification finale des processus restants...

REM Verifier si des processus Python du projet sont encore actifs
REM Cibler uniquement les processus dans le dossier transcription-audio
set "found=0"
set "project_path=%CD%"

for /f "tokens=2" %%p in ('wmic process where "name='pythonw.exe' and CommandLine like '%%transcription-audio%%'" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    set "pid=%%p"
    set "found=1"
    
    REM Verifier que ce n'est pas un processus batch/cmd (notre script)
    wmic process where "ProcessId=!pid!" get CommandLine /format:csv 2^>nul | findstr /i /c:"main.py" /c:"ui.visualizer" /c:"api.server" >nul
    if !errorlevel! equ 0 (
        echo   [WARN] Processus restant detecte PID: !pid!
        echo   [ACTION] Arret force...
        taskkill /F /PID !pid! >nul 2>&1
    )
)

if !found! equ 1 (
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
echo Les scripts batch restent actifs (protection).
echo.
timeout /t 2 /nobreak >nul
