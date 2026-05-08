#!/usr/bin/env python3
"""J.A.R.V.I.S v3.0 — Entry Point."""
import sys, os, signal
from pathlib import Path

# Sicherstellen, dass das Projektverzeichnis im Python-Path ist
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui import JARVISWindow
from core.logger import get_logger

logger = get_logger("Main")

def main():
    # High DPI
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("J.A.R.V.I.S")
    app.setApplicationVersion("3.0")

    # Graceful Shutdown
    def signal_handler(sig, frame):
        print("\n[J.A.R.V.I.S] Shutdown signal received...")
        app.quit()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Windows-spezifisch: Timer für Signal-Handling in Qt
    timer = app.startTimer(200)

    window = JARVISWindow()
    window.show()

    logger.info("🚀 J.A.R.V.I.S v3.0 gestartet")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
