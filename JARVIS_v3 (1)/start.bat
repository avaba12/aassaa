@echo off
title J.A.R.V.I.S v3.0
color 0a
cd /d "%~dp0"

echo.
echo ============================================
echo   J.A.R.V.I.S v3.0
echo ============================================
echo.

call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [FEHLER] venv nicht gefunden!
    echo Fuehre zuerst install.bat aus.
    pause
    exit /b 1
)

set PYTHONUNBUFFERED=1
set PYTHONDONTWRITEBYTECODE=1

echo [INFO] Pruefe Ollama...
python -c "import urllib.request; urllib.request.urlopen('http://localhost:11434', timeout=3)" >nul 2>&1
if errorlevel 1 (
    echo [WARNUNG] Ollama laeuft nicht!
    echo Bitte starte Ollama: https://ollama.com
echo.
)

echo [INFO] Pruefe Offline-Modelle...
if exist "models\piper\piper.exe" (
    echo [OK] Piper TTS bereit
) else (
    echo [INFO] Piper wird beim ersten TTS-Aufruf automatisch geladen.
)
if exist "models\vosk-model-small-de-0.15" (
    echo [OK] Vosk STT bereit
) else (
    echo [INFO] Vosk wird beim ersten STT-Aufruf automatisch geladen.
)

echo.
echo [INFO] Konfiguration:
python -c "import json; c=json.load(open('config/settings.json')); print('  User:', c.get('user_name','Sir')); print('  TTS:', c.get('tts_engine','piper')); print('  Offline:', c.get('offline_mode',True)); print('  Wake-Word:', c.get('wake_word','jarvis'))"
echo.

echo ============================================
echo   Starte J.A.R.V.I.S...
echo ============================================
echo [INFO] Alle Logs erscheinen hier in ECHTZEIT:
echo.

python -u "main.py"

echo.
echo ============================================
echo   J.A.R.V.I.S wurde beendet.
echo ============================================
pause
