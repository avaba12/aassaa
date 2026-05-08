#!/usr/bin/env python3
"""Download Piper TTS + deutsche Stimme."""
import os, urllib.request, zipfile, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PIPER_DIR = BASE / "models" / "piper"
PIPER_DIR.mkdir(parents=True, exist_ok=True)

PIPER_URL = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/medium/"

def setup():
    print("="*50)
    print("  Piper TTS Setup")
    print("="*50)

    if (PIPER_DIR / "piper.exe").exists() and (PIPER_DIR / "thorsten-de-medium.onnx").exists():
        print("[OK] Piper ist bereits installiert.")
        return True

    piper_zip = PIPER_DIR / "piper.zip"
    if not (PIPER_DIR / "piper.exe").exists():
        print("[INFO] Lade Piper Binary herunter...")
        try:
            urllib.request.urlretrieve(PIPER_URL, str(piper_zip))
            print("[INFO] Extrahiere Piper...")
            with zipfile.ZipFile(piper_zip, 'r') as z:
                z.extractall(PIPER_DIR)
            piper_zip.unlink()
            print("[OK] Piper extrahiert")
        except Exception as e:
            print(f"[FEHLER] Piper-Download fehlgeschlagen: {e}")
            return False

    model_file = PIPER_DIR / "thorsten-de-medium.onnx"
    if not model_file.exists():
        print("[INFO] Lade deutsche Stimme herunter... (~40MB)")
        try:
            urllib.request.urlretrieve(VOICE_BASE + "de_DE-thorsten-medium.onnx", str(model_file))
            config_file = PIPER_DIR / "thorsten-de-medium.onnx.json"
            urllib.request.urlretrieve(VOICE_BASE + "de_DE-thorsten-medium.onnx.json", str(config_file))
            print("[OK] Stimme bereit")
        except Exception as e:
            print(f"[FEHLER] Stimme-Download fehlgeschlagen: {e}")
            return False

    print("[OK] Piper TTS bereit!")
    return True

if __name__ == "__main__":
    success = setup()
    sys.exit(0 if success else 1)
