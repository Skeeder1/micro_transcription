@echo off
echo ========================================
echo TEST DIAGNOSTIC SSE
echo ========================================
echo.

echo [1/3] Test ping serveur SSE...
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -c "import urllib.request; print('PONG:', urllib.request.urlopen('http://127.0.0.1:5432/ping', timeout=2).read().decode())" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERREUR: Serveur ne repond pas!
    echo Lancez d'abord: run_enhanced.bat
    pause
    exit /b 1
)

echo.
echo [2/3] Verification Flask dans venv...
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -c "import flask; print('Flask version:', flask.__version__)"

echo.
echo [3/3] Test EventSource (ouvrir navigateur)...
echo Ouvrez test_sse_client.html dans votre navigateur
echo Le status devrait devenir VERT si SSE fonctionne

echo.
echo ========================================
echo Si tout est OK mais preview ne marche pas:
echo - Verifiez logs "[SSE] Nouveau client connecte"
echo - Parlez et verifiez "[SSE] Envoi a X client(s)"
echo ========================================
pause
