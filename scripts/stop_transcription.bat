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

REM Fonction pour tuer les processus par pattern de ligne de commande
REM Utilise tasklist au lieu de wmic pour plus de fiabilite

REM Tuer le processus principal (main.py) - exclure cmd.exe et batch scripts
echo [1/3] Arret du module CORE (main.py)...

REM Utiliser PowerShell avec WMI pour un filtrage plus precis
powershell -NoProfile -Command "$processes = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*main.py*' -and $_.CommandLine -like '*transcription-audio*' }; if ($processes) { $processes | ForEach-Object { Write-Host \"  [INFO] Arret processus CORE PID: $($_.ProcessId)\"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } } else { Write-Host '  [INFO] Aucun processus CORE trouve' }"

echo   [OK] Module CORE arrete

echo.
echo [2/3] Arret du module UI (visualizer)...

REM Tuer les processus UI avec PowerShell et WMI
powershell -NoProfile -Command "$processes = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and ($_.CommandLine -like '*ui.visualizer*' -or $_.CommandLine -like '*-m ui*') -and $_.CommandLine -like '*transcription-audio*' }; if ($processes) { $processes | ForEach-Object { Write-Host \"  [INFO] Arret processus UI PID: $($_.ProcessId)\"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } } else { Write-Host '  [INFO] Aucun processus UI trouve' }"

echo   [OK] Module UI arrete

echo.
echo [3/3] Arret du module API (Flask)...

REM Tuer les processus Flask/Werkzeug (api.server) avec PowerShell et WMI
powershell -NoProfile -Command "$processes = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*api.server*' -and $_.CommandLine -like '*transcription-audio*' }; if ($processes) { $processes | ForEach-Object { Write-Host \"  [INFO] Arret processus API PID: $($_.ProcessId)\"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } } else { Write-Host '  [INFO] Aucun processus API trouve' }"

echo   [OK] Module API arrete

echo.
echo [INFO] Verification finale des processus restants...

REM Verifier si des processus Python du projet sont encore actifs avec PowerShell et WMI
powershell -NoProfile -Command "$processes = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*transcription-audio*' -and ($_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*ui.visualizer*' -or $_.CommandLine -like '*-m ui*' -or $_.CommandLine -like '*api.server*') }; if ($processes) { Write-Host '  [WARN] Processus restants detectes:'; $processes | ForEach-Object { Write-Host \"    PID: $($_.ProcessId) - $($_.Name) - $($_.CommandLine.Substring(0, [Math]::Min(80, $_.CommandLine.Length)))\"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host '  [OK] Nettoyage force termine' } else { Write-Host '  [OK] Aucun processus du projet restant' }"

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
