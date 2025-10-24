# Script PowerShell pour arreter tous les processus du projet
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Arret du Systeme de Dictee Vocale v3.0" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Arret du module UI..." -ForegroundColor Yellow
$uiProcesses = Get-WmiObject Win32_Process | Where-Object {
    ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and
    $_.CommandLine -like '*-m ui*'
}
if ($uiProcesses) {
    foreach ($proc in $uiProcesses) {
        Write-Host "  [INFO] Arret processus UI PID: $($proc.ProcessId)" -ForegroundColor Green
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  [INFO] Aucun processus UI trouve" -ForegroundColor Gray
}
Write-Host "  [OK] Module UI arrete" -ForegroundColor Green
Write-Host ""

Write-Host "[2/2] Arret du module CORE..." -ForegroundColor Yellow
$coreProcesses = Get-WmiObject Win32_Process | Where-Object {
    ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and
    $_.CommandLine -like '*main.py*' -and
    $_.CommandLine -notlike '*pylint*' -and
    $_.CommandLine -notlike '*lsp_server*'
}
if ($coreProcesses) {
    foreach ($proc in $coreProcesses) {
        Write-Host "  [INFO] Arret processus CORE PID: $($proc.ProcessId)" -ForegroundColor Green
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  [INFO] Aucun processus CORE trouve" -ForegroundColor Gray
}
Write-Host "  [OK] Module CORE arrete" -ForegroundColor Green
Write-Host ""

Write-Host "[INFO] Verification finale..." -ForegroundColor Yellow
Start-Sleep -Milliseconds 500
$remainingProcesses = Get-WmiObject Win32_Process | Where-Object {
    ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and
    (($_.CommandLine -like '*main.py*' -and $_.CommandLine -notlike '*pylint*' -and $_.CommandLine -notlike '*lsp_server*') -or
     $_.CommandLine -like '*-m ui*')
}
if ($remainingProcesses) {
    Write-Host "  [WARN] Processus restants detectes:" -ForegroundColor Red
    foreach ($proc in $remainingProcesses) {
        Write-Host "    PID: $($proc.ProcessId) - $($proc.CommandLine.Substring(0, [Math]::Min(80, $proc.CommandLine.Length)))" -ForegroundColor Red
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  [OK] Nettoyage force termine" -ForegroundColor Green
} else {
    Write-Host "  [OK] Aucun processus du projet restant" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Arret termine - Tous les modules arretes" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
