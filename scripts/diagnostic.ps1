# Script PowerShell pour diagnostiquer les processus Python du projet

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTIC PROCESSUS - Transcription Audio" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Recherche de TOUS les processus Python/Pythonw en cours..." -ForegroundColor Yellow
Write-Host ""

$pythonProcesses = Get-WmiObject Win32_Process | Where-Object { $_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe' }

if ($pythonProcesses) {
    Write-Host "TOUS LES PROCESSUS PYTHON/PYTHONW:" -ForegroundColor Green
    Write-Host "=================================" -ForegroundColor Green
    foreach ($proc in $pythonProcesses) {
        Write-Host ""
        Write-Host "PID: $($proc.ProcessId)" -ForegroundColor White
        Write-Host "Name: $($proc.Name)" -ForegroundColor White
        Write-Host "CommandLine: $($proc.CommandLine)" -ForegroundColor Gray
        Write-Host "---"
    }
    Write-Host ""
} else {
    Write-Host "Aucun processus Python trouve!" -ForegroundColor Red
    Write-Host ""
}

Write-Host "FILTRAGE PAR PATTERN:" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan
Write-Host ""

# Test main.py
Write-Host "[1] Processus avec 'main.py':" -ForegroundColor Yellow
$mainProc = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*main.py*' }
if ($mainProc) {
    foreach ($proc in $mainProc) {
        Write-Host "  PID: $($proc.ProcessId) | $($proc.CommandLine)" -ForegroundColor Green
    }
} else {
    Write-Host "  Aucun trouve" -ForegroundColor Red
}
Write-Host ""

# Test UI
Write-Host "[2] Processus avec 'ui.visualizer' ou '-m ui':" -ForegroundColor Yellow
$uiProc = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and ($_.CommandLine -like '*ui.visualizer*' -or $_.CommandLine -like '*-m ui*') }
if ($uiProc) {
    foreach ($proc in $uiProc) {
        Write-Host "  PID: $($proc.ProcessId) | $($proc.CommandLine)" -ForegroundColor Green
    }
} else {
    Write-Host "  Aucun trouve" -ForegroundColor Red
}
Write-Host ""

# Test transcription-audio
Write-Host "[3] Processus avec 'transcription-audio':" -ForegroundColor Yellow
$projectProc = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*transcription-audio*' }
if ($projectProc) {
    foreach ($proc in $projectProc) {
        Write-Host "  PID: $($proc.ProcessId) | $($proc.CommandLine)" -ForegroundColor Green
    }
} else {
    Write-Host "  Aucun trouve" -ForegroundColor Red
}
Write-Host ""

# Test api.server
Write-Host "[4] Processus avec 'api.server' (devrait etre vide - c'est un thread):" -ForegroundColor Yellow
$apiProc = Get-WmiObject Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -like '*api.server*' }
if ($apiProc) {
    foreach ($proc in $apiProc) {
        Write-Host "  PID: $($proc.ProcessId) | $($proc.CommandLine)" -ForegroundColor Green
    }
} else {
    Write-Host "  Aucun trouve (NORMAL - API est un thread)" -ForegroundColor Green
}
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "FIN DU DIAGNOSTIC" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
