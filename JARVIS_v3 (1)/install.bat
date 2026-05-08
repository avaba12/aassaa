@echo off
title J.A.R.V.I.S v3.0 — Installation
color 0a
cd /d "%~dp0"

echo.
echo ============================================
echo   J.A.R.V.I.S v3.0 — Automatische Installation
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python ist nicht installiert!
    pause
    exit /b 1
)
python --version
echo.

if not exist "venv" (
    echo [2/7] Erstelle virtuelle Umgebung...
    python -m venv "venv"
    if errorlevel 1 (
        echo [FEHLER] venv konnte nicht erstellt werden!
        pause
        exit /b 1
    )
    echo [OK] venv erstellt
) else (
    echo [OK] venv existiert bereits
)
echo.

echo [3/7] Aktiviere virtuelle Umgebung...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [FEHLER] venv konnte nicht aktiviert werden!
    pause
    exit /b 1
)
echo [OK] venv aktiviert
echo.

echo [4/7] Upgrade pip...
python -m pip install --upgrade pip setuptools wheel
echo.

echo [5/7] Installiere Python-Pakete...
pip install PyQt6 requests psutil ollama pyttsx3 soundfile pyaudio SpeechRecognition vosk pyautogui pyperclip mss Pillow opencv-python numpy python-dotenv pydantic send2trash PyPDF2 pdfplumber python-docx beautifulsoup4 edge-tts duckduckgo-search playwright google-generativeai google-genai
echo.
echo [OK] Python-Pakete installiert
echo.

echo [6/7] Installiere Playwright Browser...
python -m playwright install chromium
echo.

echo [7/7] Lade Offline-Modelle...
echo.
echo   [7a] Piper TTS (~70MB)...
python "setup_piper.py"
echo.
echo   [7b] Vosk STT (~50MB)...
python "setup_vosk.py"
echo.

echo [INFO] Erstelle Konfiguration...
if not exist "config\settings.json" (
    python -c "import json; open('config/settings.json','w').write(json.dumps({'user_name':'Sir','language':'de-DE','theme':'dark','tts_engine':'piper','tts_voice':'thorsten-de-medium','tts_speed':1.0,'tts_volume':0.9,'wake_word':'jarvis','sleep_word':'danke schlaf','ollama_host':'http://localhost:11434','chat_model':'llama3','code_model':'codellama','vision_model':'llava','temperature':0.7,'top_p':0.9,'memory_limit':1000,'auto_cleanup':True,'pin_enabled':False,'pin_code':'','session_timeout':30,'confirmation_required':True,'offline_mode':True,'use_local_wake_word':True,'show_thinking':False,'thinking_mode':'instant','skills':{'web_search':True,'file_access':True,'comfyui':False,'pc_control':True,'plugins':True,'telegram':False,'discord':False,'home_assistant':False,'obsidian':False,'voice_control':True,'rag':True},'master_mode':'standard'},indent=4))"
    echo [OK] Konfiguration erstellt
) else (
    echo [OK] Konfiguration existiert bereits
)
echo.

echo ============================================
echo   INSTALLATION ABGESCHLOSSEN!
echo ============================================
echo.
echo [OK] Alles ist installiert und bereit!
echo.
echo [INFO] Starte J.A.R.V.I.S jetzt mit: start.bat
echo.
pause
