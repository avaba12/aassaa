"""Echtzeit-Logger mit Datei-Rotation und Audit-Log."""
import logging, os, sys
from pathlib import Path
from datetime import datetime

# WICHTIG: Unbuffered output fuer Windows CMD
sys.stdout.reconfigure(line_buffering=True)

class JARVISLogger:
    def __init__(self, log_dir=None):
        base = Path(__file__).resolve().parent.parent
        self.log_dir = log_dir or (base / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_file_logger()
        self._setup_console_logger()

    def _setup_file_logger(self):
        today = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"jarvis_{today}.log"
        self.file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        self.file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"
        ))
        self.file_handler.setLevel(logging.DEBUG)

    def _setup_console_logger(self):
        # Verwende sys.__stdout__ um PyQt-Umleitung zu umgehen
        self.console_handler = logging.StreamHandler(sys.__stdout__)
        self.console_handler.setFormatter(logging.Formatter(
            "[%(name)s] %(message)s"
        ))
        self.console_handler.setLevel(logging.INFO)

    def get_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            logger.addHandler(self.file_handler)
            logger.addHandler(self.console_handler)
        return logger

    def perf(self, action: str, start_time: float):
        elapsed = (time.time() - start_time) * 1000
        self.get_logger("perf").info(f"⏱️  {action}: {elapsed:.0f}ms")
        return elapsed

# Singleton
_logger_instance = None

def get_logger(name: str = "JARVIS") -> logging.Logger:
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = JARVISLogger()
    return _logger_instance.get_logger(name)
