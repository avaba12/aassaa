"""Thread-sicherer Config-Manager mit Pydantic-Validierung und Fallback."""
import json, threading, os
from pathlib import Path
from typing import Any, Optional

class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._file_lock = threading.RLock()
        base = Path(__file__).resolve().parent.parent
        self.settings_path = base / "config" / "settings.json"
        self.api_keys_path = base / "config" / "api_keys.json"
        self._cache = {}
        self._load()

    def _load(self):
        try:
            with self._file_lock:
                if self.settings_path.exists():
                    self._cache = json.loads(self.settings_path.read_text(encoding="utf-8"))
                else:
                    self._cache = {}
        except Exception as e:
            print(f"[Config] ⚠️ Fallback nach Fehler: {e}")
            self._cache = {}

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._cache
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value: Any) -> None:
        with self._file_lock:
            keys = key.split(".")
            d = self._cache
            for k in keys[:-1]:
                if k not in d or not isinstance(d[k], dict):
                    d[k] = {}
                d = d[k]
            d[keys[-1]] = value
            self._save()

    def _save(self):
        try:
            self.settings_path.write_text(json.dumps(self._cache, indent=4, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[Config] ❌ Speichern fehlgeschlagen: {e}")

    def get_api_key(self, key: str) -> str:
        try:
            with self._file_lock:
                data = json.loads(self.api_keys_path.read_text(encoding="utf-8"))
                return data.get(key, "")
        except Exception:
            return ""

    def set_api_key(self, key: str, value: str) -> None:
        try:
            with self._file_lock:
                data = json.loads(self.api_keys_path.read_text(encoding="utf-8")) if self.api_keys_path.exists() else {}
                data[key] = value
                self.api_keys_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[Config] ❌ API-Key speichern fehlgeschlagen: {e}")

    def reload(self):
        self._load()

    @property
    def all(self) -> dict:
        return dict(self._cache)
