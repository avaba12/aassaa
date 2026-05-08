# J.A.R.V.I.S v3.0

**Just A Rather Very Intelligent System** — Dein lokaler KI-Assistent.

## 🚀 Schnellstart

### 1. Voraussetzungen
- **Python 3.10+** (https://python.org)
- **Ollama** (https://ollama.com) — für lokale KI-Modelle
- **AMD ROCm** (optional, für GPU-Monitoring)

### 2. Installation
```batch
:: ZIP entpacken, dann im Explorer:
Doppelklick auf install.bat
```

### 3. Start
```batch
Doppelklick auf start.bat
```

## 🔒 OFFLINE-MODUS (Standard)

J.A.R.V.I.S läuft **komplett offline** — kein Internet nötig!

| Feature | Offline | Online |
|---------|---------|--------|
| **KI-Chat** | ✅ Ollama (lokal) | ✅ Ollama |
| **TTS** | ✅ Piper / pyttsx3 | ✅ + Edge-TTS |
| **STT** | ✅ Vosk (lokal) | ✅ + Google Speech |
| **Wake-Word** | ✅ Lokal (Energie+Vosk) | ✅ + Porcupine |
| **Web-Suche** | ❌ Blockiert | ✅ DuckDuckGo + Gemini |
| **Gemini API** | ❌ Blockiert | ✅ Falls Key vorhanden |

**Umstellung:** Einstellungen → KI → "Offline-Modus" Toggle

## 🎮 Features

| Feature | Status |
|---------|--------|
| **KI-Chat** (Ollama, offline) | ✅ 3 Profile: Chat / Code / Vision |
| **Auto-Detect** | ✅ Erkennt "Python" → Code, "Bild" → Vision |
| **TTS** | ✅ Piper (offline) → pyttsx3 → Edge-TTS (online) |
| **STT** | ✅ Vosk (offline) → Google Speech (online) |
| **Wake-Word** | ✅ Lokal ohne Key → Porcupine (online mit Key) |
| **GPU-Monitor** | ✅ AMD ROCm + NVIDIA + Intel |
| **VRAM-Clear** | ✅ Automatisch bei Modell-Wechsel |
| **Skill-System** | ✅ 11 Skills + Berechtigungen + Master-Modi |
| **Memory** | ✅ SQLite, Write-Queue, Auto-Cleanup |
| **Security** | ✅ PIN, Session-Timeout, Bestätigungen |
| **Model-Manager** | ✅ Install/Delete/Switch + VRAM-Schätzung |
| **Settings** | ✅ 8 Tabs (KI, User, Security, Skills, Memory, UI, Integrationen) |
| **Web-Search** | ✅ DuckDuckGo + Gemini (nur Online) |
| **PC-Steuerung** | ✅ Apps öffnen, Screenshots, Tastatur/Maus |
| **Datei-Manager** | ✅ Lesen, Schreiben, Suchen, Löschen (Papierkorb) |

## 🛡️ Sicherheit

- **Bestätigungs-Dialog** für alle gefährlichen Aktionen (Löschen, etc.)
- **PIN-Schutz** optional
- **Session-Timeout** nach Inaktivität
- **Skill-Berechtigungen** granulare Kontrolle
- **Master-Modi**: Admin / Standard / Gast

## 🎙️ Sprachsteuerung

| Befehl | Funktion |
|--------|----------|
| "Jarvis" (Wake-Word) | Weckt J.A.R.V.I.S auf |
| "Danke schlaf" (Sleep-Word) | Schickt J.A.R.V.I.S schlafen |
| 🔇 Button | Mikrofon stumm schalten |

**Offline:** Wake-Word funktioniert lokal über Energie-Erkennung + Vosk — kein Internet, kein API-Key nötig!

## 🎮 GPU-Monitoring

Unterstützt:
- **AMD** via ROCm-SMI
- **NVIDIA** via nvidia-smi
- **Intel** via WMI (Fallback)

## 📁 Verzeichnisstruktur

```
JARVIS_v3/
├── main.py              # Entry Point
├── ui.py                # PyQt6 Hauptfenster
├── requirements.txt     # Python-Abhängigkeiten
├── setup.py             # Erstmaliges Setup
├── setup_piper.py       # Optional: Piper TTS Download (70MB)
├── setup_vosk.py        # Optional: Vosk STT Download (50MB)
├── install.bat          # 1-Klick Installation
├── start.bat            # 1-Klick Start
├── core/
│   ├── ai_engine.py     # Ollama KI-Engine
│   ├── gpu_monitor.py   # GPU-Monitoring
│   ├── security.py      # PIN, Session, Rate-Limit
│   ├── skill_manager.py # 11 Skills + Berechtigungen
│   ├── logger.py        # Logging + Audit
│   ├── voice/           # TTS-Engine (Piper/Edge/pyttsx3)
│   └── stt/             # STT-Listener (Vosk/Google)
├── agent/
│   ├── planner.py       # Task-Planung
│   ├── executor.py      # Task-Ausführung
│   ├── error_handler.py # Fehlerbehandlung
│   └── task_queue.py    # Hintergrund-Queue
├── actions/
│   ├── open_app.py      # Apps öffnen
│   ├── web_search.py    # Websuche (nur Online)
│   ├── file_controller.py # Datei-Manager
│   ├── computer_control.py # PC-Steuerung
│   └── ...              # Weitere Actions
├── memory/
│   ├── config_manager.py # Thread-sichere Config
│   └── memory_manager.py # SQLite Memory
├── config/
│   ├── settings.json    # Alle Einstellungen
│   └── api_keys.json    # API-Keys
└── models/
    ├── piper/           # Piper-Stimmen (optional)
    └── vosk-model-small-de-0.15/  # Vosk STT (optional)
```

## ⚠️ Bekannte Einschränkungen

1. **Piper TTS** — `python setup_piper.py` für 70MB Download (einmalig)
2. **Vosk STT** — `python setup_vosk.py` für 50MB Download (einmalig)
3. **ComfyUI-Integration** ist vorbereitet, aber noch nicht vollständig
4. **Telegram/Discord/Home Assistant** sind als Config vorbereitet, aber nicht aktiv angebunden

## 📝 Changelog

### v3.0
- Kompletter Rewrite basierend auf Mark-XXXIX
- Umbenannt zu J.A.R.V.I.S
- **Offline-Modus als Standard** — komplett lokal ohne Internet
- PyQt6 UI mit Dark Theme
- 8-Tabs Settings-Fenster mit Offline/Online Toggle
- TTS mit 3 Engines (Piper offline / Edge online / pyttsx3 offline)
- STT mit Vosk (offline) + Google (online)
- Lokales Wake-Word ohne API-Key
- GPU-Monitor mit VRAM-Clear
- Skill-System mit Berechtigungen
- Bestätigungs-System für gefährliche Aktionen
- Mikrofon-Mute-Button
