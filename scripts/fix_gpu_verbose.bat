@echo off
chcp 65001 >nul
echo ============================================================
echo INSTALLATION PYTORCH + CUDA (MODE VERBOSE)
echo ============================================================
echo.

cd /d "%~dp0\.."

echo [1/6] Vérification de l'environnement virtuel...
if not exist .venv\Scripts\python.exe (
    echo ❌ ERREUR: Environnement virtuel non trouvé
    pause
    exit /b 1
)
echo    ✅ Environnement virtuel trouvé
echo.

echo [2/6] Vérification de pip...
.venv\Scripts\python.exe -m pip --version
if %ERRORLEVEL% NEQ 0 (
    echo ❌ ERREUR: pip non fonctionnel
    pause
    exit /b 1
)
echo.

echo [3/6] Mise à jour de pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
echo.

echo [4/6] Désinstallation de PyTorch existant...
.venv\Scripts\pip.exe uninstall torch torchvision torchaudio -y
echo    ✅ Nettoyage effectué
echo.

echo [5/6] Installation de PyTorch avec CUDA 12.1...
echo    URL: https://download.pytorch.org/whl/cu121
echo    Package: torch torchvision torchaudio
echo.
echo    ATTENTION: Téléchargement ~2 GB, cela peut prendre 5-10 minutes
echo    Ne fermez pas cette fenêtre !
echo.
.venv\Scripts\pip.exe install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo ❌ ERREUR LORS DE L'INSTALLATION
    echo ============================================================
    echo.
    echo Causes possibles:
    echo 1. Problème de connexion internet
    echo 2. Espace disque insuffisant (besoin de ~5 GB libres)
    echo 3. Problème de permissions
    echo 4. Antivirus bloquant le téléchargement
    echo.
    echo Solutions:
    echo 1. Vérifiez votre connexion internet
    echo 2. Libérez de l'espace disque
    echo 3. Essayez de lancer ce script en administrateur
    echo 4. Désactivez temporairement l'antivirus
    echo.
    echo Ou essayez l'installation manuelle:
    echo    cd C:\GitHub\transcription-audio
    echo    .venv\Scripts\activate
    echo    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    echo.
    pause
    exit /b 1
)
echo.
echo    ✅ PyTorch installé avec succès
echo.

echo [6/6] Vérification de l'installation...
.venv\Scripts\python.exe -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA disponible:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Vérification échouée
    pause
    exit /b 1
)
echo.

echo ============================================================
echo ✅ INSTALLATION RÉUSSIE !
echo ============================================================
echo.
echo Votre GPU RTX 4060 est maintenant prêt à être utilisé !
echo.
echo Prochaines étapes:
echo 1. Fermez toutes les instances de l'application
echo 2. Lancez: scripts\start_transcription_debug.bat
echo 3. Cherchez dans les logs: "Device: CUDA"
echo.
echo Le modèle 'large' devrait maintenant être 10-20x plus rapide !
echo ============================================================
pause
