# Script PowerShell pour lancer main_enhanced.py avec venv
# Garantit l'utilisation du bon environnement Python

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Systeme de Dictee Vocale Avance" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Chemin du venv
$venvPython = "C:\GitHub\transcription-audio\.venv\Scripts\python.exe"

# Verifier que le venv existe
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERREUR] Virtual environment introuvable!" -ForegroundColor Red
    Write-Host "Verifiez que .venv existe dans ce dossier." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# Afficher version Python
Write-Host "[INFO] Utilisation du venv Python:" -ForegroundColor Green
& $venvPython --version
Write-Host ""

# Verifier Flask
Write-Host "[INFO] Verification de Flask..." -ForegroundColor Yellow
try {
    & $venvPython -c "from flask import Flask; print('Flask OK')" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Flask non installe"
    }
    Write-Host "[OK] Flask installe" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Flask non installe. Installation en cours..." -ForegroundColor Yellow
    & $venvPython -m pip install flask
}

Write-Host ""
Write-Host "[INFO] Lancement de main_enhanced.py..." -ForegroundColor Cyan
Write-Host ""

# Lancer main_enhanced.py
& $venvPython main_enhanced.py

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Programme termine" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Read-Host "Appuyez sur Entree pour quitter"
