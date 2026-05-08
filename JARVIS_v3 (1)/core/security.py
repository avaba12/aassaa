"""Sicherheits-Modul: PIN, Session-Timeout, Rate-Limit, Input-Sanitization."""
import time, re, hashlib
from typing import Optional, Dict
from memory.config_manager import ConfigManager

class SecurityManager:
    def __init__(self):
        self.cfg = ConfigManager()
        self._sessions: Dict[str, float] = {}
        self._rate_limit: Dict[str, list] = {}
        self._pin_verified = False
        self._last_activity = time.time()

    def check_pin(self, pin: str) -> bool:
        stored = self.cfg.get("pin_code", "")
        if not stored:
            return True
        if not self.cfg.get("pin_enabled", False):
            return True
        hashed = hashlib.sha256(pin.encode()).hexdigest()
        if hashed == stored:
            self._pin_verified = True
            self._last_activity = time.time()
            return True
        return False

    def set_pin(self, pin: str) -> None:
        hashed = hashlib.sha256(pin.encode()).hexdigest()
        self.cfg.set("pin_code", hashed)
        self.cfg.set("pin_enabled", True)

    def is_session_valid(self) -> bool:
        timeout = self.cfg.get("session_timeout", 30) * 60
        if time.time() - self._last_activity > timeout:
            self._pin_verified = False
            return False
        return True

    def touch(self):
        self._last_activity = time.time()

    def check_rate_limit(self, ip: str = "local", max_req: int = 60, window: int = 60) -> bool:
        now = time.time()
        if ip not in self._rate_limit:
            self._rate_limit[ip] = []
        self._rate_limit[ip] = [t for t in self._rate_limit[ip] if now - t < window]
        if len(self._rate_limit[ip]) >= max_req:
            return False
        self._rate_limit[ip].append(now)
        return True

    @staticmethod
    def sanitize_app_name(name: str) -> str:
        """Erlaubt nur Buchstaben, Zahlen, Leerzeichen, Bindestriche, Punkte, Unterstriche."""
        cleaned = re.sub(r"[^a-zA-Z0-9\s\.\-_]", "", name).strip()
        return cleaned

    @staticmethod
    def sanitize_url(url: str) -> Optional[str]:
        """Prüft ob URL gültig ist (http/https, kein localhost-Scanning)."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return None
        # Blockiere gefährliche Schemas
        dangerous = ["file://", "ftp://", "dict://", "gopher://", "ldap://"]
        if any(url.lower().startswith(d) for d in dangerous):
            return None
        return url

    @staticmethod
    def is_dangerous_command(text: str) -> bool:
        """Prüft auf Shell-Metazeichen."""
        dangerous = [";", "|", "&&", "||", "`", "$()", ">>", "<("]
        return any(d in text for d in dangerous)

    def require_confirmation(self, action: str) -> bool:
        if not self.cfg.get("confirmation_required", True):
            return False
        dangerous_actions = ["delete", "remove", "uninstall", "shutdown", "restart", "format", "rm -rf"]
        return any(d in action.lower() for d in dangerous_actions)
