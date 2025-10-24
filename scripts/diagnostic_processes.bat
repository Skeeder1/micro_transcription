@echo off
REM Script de diagnostic pour identifier les processus Python du projet
REM Affiche les details des processus pour comprendre pourquoi stop_transcription.bat echoue

echo ================================================
echo DIAGNOSTIC PROCESSUS - Transcription Audio
echo ================================================
echo.

REM Changer vers le repertoire du projet
cd /d "%~dp0\.."

echo [INFO] Recherche de TOUS les processus Python/Pythonw en cours...
echo.

echo ================================================
echo TOUS LES PROCESSUS PYTHON/PYTHONW
echo ================================================
powershell -NoProfile -Command "Get-WmiObject Win32_Process | Where-Object { $_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe' } | ForEach-Object { Write-Host ''; Write-Host 'PID:' $_.ProcessId; Write-Host 'Name:' $_.Name; Write-Host 'CommandLine:' $_.CommandLine; Write-Host '---' }"

echo.
echo ================================================
echo PROCESSUS AVEC 'main.py' DANS LA COMMANDE
echo ================================================
powershell -NoProfile -Command "$processes = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*main.py*' }; if ($processes) { $processes | ForEach-Object { Write-Host ''; Write-Host 'PID:' $_.ProcessId; Write-Host 'Name:' $_.Name; Write-Host 'CommandLine:' $_.CommandLine; Write-Host 'MATCH: main.py'; Write-Host '---' } } else { Write-Host '[INFO] Aucun processus trouve avec main.py' }"

echo.
echo ================================================
echo PROCESSUS AVEC 'ui.visualizer' ou '-m ui' DANS LA COMMANDE
echo ================================================
powershell -NoProfile -Command "$processes = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and ($_.CommandLine -like '*ui.visualizer*' -or $_.CommandLine -like '*-m ui*') }; if ($processes) { $processes | ForEach-Object { Write-Host ''; Write-Host 'PID:' $_.ProcessId; Write-Host 'Name:' $_.Name; Write-Host 'CommandLine:' $_.CommandLine; Write-Host 'MATCH: UI'; Write-Host '---' } } else { Write-Host '[INFO] Aucun processus trouve avec ui.visualizer ou -m ui' }"

echo.
echo ================================================
echo PROCESSUS AVEC 'transcription-audio' DANS LA COMMANDE
echo ================================================
powershell -NoProfile -Command "$processes = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*transcription-audio*' }; if ($processes) { $processes | ForEach-Object { Write-Host ''; Write-Host 'PID:' $_.ProcessId; Write-Host 'Name:' $_.Name; Write-Host 'CommandLine:' $_.CommandLine; Write-Host 'MATCH: transcription-audio'; Write-Host '---' } } else { Write-Host '[INFO] Aucun processus trouve avec transcription-audio' }"

echo.
echo ================================================
echo PROCESSUS AVEC 'api.server' DANS LA COMMANDE
echo ================================================
powershell -NoProfile -Command "$processes = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*api.server*' }; if ($processes) { $processes | ForEach-Object { Write-Host ''; Write-Host 'PID:' $_.ProcessId; Write-Host 'Name:' $_.Name; Write-Host 'CommandLine:' $_.CommandLine; Write-Host 'MATCH: api.server'; Write-Host '---' } } else { Write-Host '[INFO] Aucun processus trouve avec api.server (NORMAL - API est un thread)' }"

echo.
echo ================================================
echo RESUME
echo ================================================
echo.
echo Ce diagnostic montre comment Windows voit les lignes de commande.
echo.
echo Utilisez ces informations pour corriger stop_transcription.bat :
echo   1. Verifier que les patterns matchent les CommandLine reelles
echo   2. Simplifier les filtres si necessaire
echo   3. Retirer la section [3/3] (api.server) car c'est un thread
echo.
echo ================================================
pause
