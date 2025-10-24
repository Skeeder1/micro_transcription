# Script PowerShell pour lancer le systeme de transcription v2.0
# Demarre tous les modules: Core, UI, API

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Systeme de Dictee Vocale Avance v2.0" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Changer vers le repertoire du projet
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path (Join-Path $scriptPath "..")

# Arreter toute instance precedente
Write-Host "[ETAPE 1/5] Arret des instances precedentes..." -ForegroundColor Yellow
$stopScript = Join-Path $scriptPath "stop_transcription.bat"
if (Test-Path $stopScript) {
    & $stopScript | Out-Null
    Start-Sleep -Seconds 1
}
Write-Host "  [OK] Instances precedentes arretees" -ForegroundColor Green
Write-Host ""

# Verifier que le venv existe
Write-Host "[ETAPE 2/5] Verification de l'environnement..." -ForegroundColor Yellow
$venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "  [ERREUR] Virtual environment introuvable!" -ForegroundColor Red
    Write-Host "  Verifiez que .venv existe dans: $(Get-Location)" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# Afficher version Python
$pythonVersion = & $venvPython --version
Write-Host "  $pythonVersion" -ForegroundColor Gray
Write-Host "  [OK] Environnement virtuel trouve" -ForegroundColor Green
Write-Host ""

# Verifier les dependances critiques
Write-Host "[ETAPE 3/5] Verification des dependances..." -ForegroundColor Yellow

# Flask
try {
    & $venvPython -c "import flask" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [WARN] Flask non installe. Installation en cours..." -ForegroundColor Yellow
        & $venvPython -m pip install flask | Out-Null
    }
} catch {
    Write-Host "  [WARN] Flask non installe. Installation en cours..." -ForegroundColor Yellow
    & $venvPython -m pip install flask | Out-Null
}

# faster-whisper
try {
    & $venvPython -c "import faster_whisper" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "faster-whisper non installe"
    }
} catch {
    Write-Host "  [ERREUR] faster-whisper non installe!" -ForegroundColor Red
    Write-Host "  Installez les dependances avec: pip install -r requirements.txt" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# PySide6
try {
    & $venvPython -c "import PySide6" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "PySide6 non installe"
    }
} catch {
    Write-Host "  [ERREUR] PySide6 non installe!" -ForegroundColor Red
    Write-Host "  Installez les dependances avec: pip install -r requirements.txt" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# sounddevice
try {
    & $venvPython -c "import sounddevice" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "sounddevice non installe"
    }
} catch {
    Write-Host "  [ERREUR] sounddevice non installe!" -ForegroundColor Red
    Write-Host "  Installez les dependances avec: pip install -r requirements.txt" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

Write-Host "  [OK] Flask - OK" -ForegroundColor Green
Write-Host "  [OK] faster-whisper - OK" -ForegroundColor Green
Write-Host "  [OK] PySide6 - OK" -ForegroundColor Green
Write-Host "  [OK] sounddevice - OK" -ForegroundColor Green
Write-Host ""

# Verifier la structure du projet
Write-Host "[ETAPE 4/5] Verification de la structure du projet..." -ForegroundColor Yellow

if (-not (Test-Path "main.py")) {
    Write-Host "  [ERREUR] main.py introuvable!" -ForegroundColor Red
    Write-Host "  Verifiez que vous etes dans le bon repertoire." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

if (-not (Test-Path "core")) {
    Write-Host "  [ERREUR] Module core/ introuvable!" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

if (-not (Test-Path "ui")) {
    Write-Host "  [ERREUR] Module ui/ introuvable!" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

if (-not (Test-Path "api")) {
    Write-Host "  [ERREUR] Module api/ introuvable!" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

Write-Host "  [OK] main.py - OK" -ForegroundColor Green
Write-Host "  [OK] Module core/ - OK" -ForegroundColor Green
Write-Host "  [OK] Module ui/ - OK" -ForegroundColor Green
Write-Host "  [OK] Module api/ - OK" -ForegroundColor Green
Write-Host "  [OK] Module shared/ - OK" -ForegroundColor Green
Write-Host ""

# Lancer l'application
Write-Host "[ETAPE 5/5] Demarrage du systeme..." -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "INFORMATIONS MODE DEBUG" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ce mode affiche tous les logs en temps reel:" -ForegroundColor Gray
Write-Host "  - Messages du module CORE (transcription)" -ForegroundColor Gray
Write-Host "  - Messages du module API (serveur Flask)" -ForegroundColor Gray
Write-Host "  - Messages du module UI (visualiseur)" -ForegroundColor Gray
Write-Host "  - Erreurs et warnings detailles" -ForegroundColor Gray
Write-Host ""
Write-Host "La console reste ouverte pour diagnostiquer les problemes." -ForegroundColor Gray
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arreter l'application." -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Seconds 2

# Lancer main.py
& $venvPython main.py

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Programme termine" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Read-Host "Appuyez sur Entree pour quitter"
