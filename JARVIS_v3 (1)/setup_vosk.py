#!/usr/bin/env python3
"""Download Vosk STT Modell (offline, ~50MB)."""
import os, urllib.request, zipfile, sys
from pathlib import Path

def download(url: str, dest: Path, desc: str = ""):
    print(f"  [Download] {desc or dest.name} ...")
    try:
        urllib.request.urlretrieve(url, str(dest))
        size = dest.stat().st_size / 1024 / 1024
        print(f"  [OK] {size:.1f} MB heruntergeladen")
        return True
    except Exception as e:
        print(f"  [FEHLER] Download fehlgeschlagen: {e}")
        return False

BASE = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip"

def setup():
    print("="*50)
    print("  Vosk STT Setup")
    print("="*50)

    model_dir = MODELS_DIR / "vosk-model-small-de-0.15"
    if model_dir.exists():
        print("[INFO] Vosk ist bereits installiert.")
        print("[OK] Vosk STT bereit!")
        return True

    model_zip = MODELS_DIR / "vosk-model-small-de-0.15.zip"
    print("[INFO] Lade deutsches STT-Modell herunter... (~50MB)")

    if not download(VOSK_URL, model_zip, "Vosk Modell"):
        print("[WARNUNG] Vosk-Download fehlgeschlagen.")
        print("[INFO] Fallback: Texteingabe oder Google Speech (Online).")
        return False

    print("[INFO] Extrahiere Vosk...")
    try:
        with zipfile.ZipFile(model_zip, 'r') as z:
            z.extractall(MODELS_DIR)
        model_zip.unlink()
        print("[OK] Vosk extrahiert")
    except Exception as e:
        print(f"[FEHLER] Extraktion fehlgeschlagen: {e}")
        return False

    print("[OK] Vosk STT bereit!")
    return True

if __name__ == "__main__":
    success = setup()
    sys.exit(0 if success else 1)
