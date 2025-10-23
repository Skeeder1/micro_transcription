@echo off
REM ================================================
REM   Visualiseur Audio - Fenetre Native
REM ================================================

echo.
echo ================================================
echo   Visualiseur Audio (Fenetre Native)
echo ================================================
echo.

REM Verifier que le venv existe
if not exist ".venv\Scripts\python.exe" (
    echo [ERREUR] Virtual environment introuvable!
    echo Verifiez que .venv existe dans ce dossier.
    echo.
    pause
    exit /b 1
)

REM Afficher version Python
echo [INFO] Utilisation du venv Python:
.venv\Scripts\python.exe --version
echo.

REM Nettoyer les instances existantes du visualiseur
echo [INFO] Fermeture des visualiseurs existants...
taskkill /FI "IMAGENAME eq pythonw.exe" /FI "WINDOWTITLE eq *visualizer*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Visualiseur Audio*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Micro Monitor*" /F >nul 2>&1
timeout /t 1 /nobreak >nul
echo [INFO] Nettoyage termine.
echo.

REM Verifier PySide6
echo [INFO] Verification de PySide6...
.venv\Scripts\python.exe -c "import PySide6; from PySide6.QtWebEngineWidgets import QWebEngineView" 2>nul
if errorlevel 1 (
    echo [WARN] PySide6 manquant. Installation en cours...
    .venv\Scripts\python.exe -m pip install -q PySide6 PySide6-WebEngine
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation de PySide6
        pause
        exit /b 1
    )
    echo [INFO] PySide6 installe avec succes
)
echo.

echo ================================================
echo   Lancement du Visualiseur
echo ================================================
echo.
echo [INFO] Caracteristiques:
echo        - Fenetre toujours au premier plan
echo        - Masquage automatique en mode veille
echo        - Appuyez sur ESC pour fermer
echo.
echo [INFO] Demarrage...
echo.

REM Lancer avec pythonw pour eviter la console
.venv\Scripts\pythonw.exe visualizer_window.py

echo.
echo [INFO] Visualiseur ferme.
