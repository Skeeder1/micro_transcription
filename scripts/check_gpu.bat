@echo off
chcp 65001 >nul
echo ============================================================
echo VÉRIFICATION GPU - TRANSCRIPTION AUDIO
echo ============================================================
echo.

cd /d "%~dp0\.."

echo [1] Driver NVIDIA:
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo    ❌ nvidia-smi non disponible - Pas de GPU NVIDIA détecté
) else (
    echo    ✅ GPU NVIDIA détecté
)
echo.

echo [2] PyTorch CUDA:
.venv\Scripts\python.exe -c "import torch; print('   PyTorch:', torch.__version__); print('   CUDA disponible:', torch.cuda.is_available()); print('   Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo    ❌ PyTorch non installé ou erreur
    echo    → Exécutez: scripts\fix_gpu.bat
)
echo.

echo [3] faster-whisper avec GPU:
.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; m = WhisperModel('tiny', device='cuda'); print('   ✅ faster-whisper peut utiliser le GPU'); del m" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo    ❌ faster-whisper ne peut pas utiliser le GPU
    echo    → Exécutez: scripts\fix_gpu.bat
)
echo.

echo ============================================================
echo RÉSULTAT:
echo.
.venv\Scripts\python.exe -c "import torch; print('GPU utilisable pour transcription:', '✅ OUI' if torch.cuda.is_available() else '❌ NON')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Configuration GPU non fonctionnelle
    echo.
    echo ACTION REQUISE:
    echo    Exécutez: scripts\fix_gpu.bat
)
echo ============================================================
echo.
pause
