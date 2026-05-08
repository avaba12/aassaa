"""Skill-System mit JSON-basierten dynamischen Skills + Import/Export."""
import json
from pathlib import Path
from memory.config_manager import ConfigManager

class SkillManager:
    SKILLS = {
        "web_search": {"name": "Web-Suche", "desc": "Internet-Suche via DuckDuckGo/Google", "perms": ["internet"], "builtin": True},
        "file_access": {"name": "Datei-Zugriff", "desc": "Dateien lesen/schreiben/verwalten", "perms": ["read_files", "write_files"], "builtin": True},
        "comfyui": {"name": "ComfyUI", "desc": "Bild/Video/Musik generieren", "perms": ["gpu_vram", "write_files"], "builtin": True},
        "pc_control": {"name": "PC-Steuerung", "desc": "Apps starten, System steuern", "perms": ["run_apps", "system_cmds"], "builtin": True},
        "plugins": {"name": "Plugins", "desc": "Benutzerdefinierte Plugins ausfuehren", "perms": ["run_apps", "system_cmds"], "builtin": True},
        "telegram": {"name": "Telegram", "desc": "Telegram-Bot Integration", "perms": ["internet"], "builtin": True},
        "discord": {"name": "Discord", "desc": "Discord-Rich-Presence", "perms": ["internet"], "builtin": True},
        "home_assistant": {"name": "Home Assistant", "desc": "Smart-Home Steuerung", "perms": ["internet"], "builtin": True},
        "obsidian": {"name": "Obsidian", "desc": "Notizen exportieren", "perms": ["write_files"], "builtin": True},
        "voice_control": {"name": "Sprachsteuerung", "desc": "Wake-Word, STT, TTS", "perms": ["microphone", "tts"], "builtin": True},
        "rag": {"name": "RAG", "desc": "Dokumente durchsuchen", "perms": ["read_files"], "builtin": True},
    }

    MASTER_MODES = {
        "admin": {"desc": "Alles erlaubt", "blocks": []},
        "standard": {"desc": "Nur sichere Berechtigungen", "blocks": ["system_cmds", "shutdown", "restart"]},
        "guest": {"desc": "Nur Chat", "blocks": ["internet", "read_files", "write_files", "gpu_vram", "run_apps", "system_cmds", "microphone", "tts"]},
    }

    def __init__(self):
        self.cfg = ConfigManager()
        self._skills_file = Path(__file__).resolve().parent.parent / "config" / "skills.json"
        self._load_custom_skills()

    def _load_custom_skills(self):
        """Lädt benutzerdefinierte Skills aus skills.json."""
        if self._skills_file.exists():
            try:
                custom = json.loads(self._skills_file.read_text(encoding="utf-8"))
                for key, data in custom.items():
                    if key not in self.SKILLS:
                        self.SKILLS[key] = {**data, "builtin": False}
            except Exception:
                pass

    def _save_custom_skills(self):
        """Speichert benutzerdefinierte Skills."""
        custom = {k: v for k, v in self.SKILLS.items() if not v.get("builtin", True)}
        try:
            self._skills_file.write_text(json.dumps(custom, indent=4, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[SkillManager] Fehler beim Speichern: {e}")

    def is_enabled(self, skill: str) -> bool:
        skills = self.cfg.get("skills", {})
        return skills.get(skill, False)

    def toggle(self, skill: str, state: bool):
        self.cfg.set(f"skills.{skill}", state)

    def check_permission(self, permission: str) -> bool:
        mode = self.cfg.get("master_mode", "standard")
        blocks = self.MASTER_MODES.get(mode, {}).get("blocks", [])
        return permission not in blocks

    def can_use_skill(self, skill: str) -> tuple:
        if not self.is_enabled(skill):
            return False, f"Skill '{self.SKILLS.get(skill, {}).get('name', skill)}' ist deaktiviert."
        skill_info = self.SKILLS.get(skill, {})
        for perm in skill_info.get("perms", []):
            if not self.check_permission(perm):
                return False, f"Berechtigung '{perm}' ist im Modus '{self.cfg.get('master_mode', 'standard')}' blockiert."
        return True, ""

    def get_all(self) -> dict:
        skills_cfg = self.cfg.get("skills", {})
        result = {}
        for key, info in self.SKILLS.items():
            result[key] = {**info, "enabled": skills_cfg.get(key, False)}
        return result

    def add_skill(self, key: str, name: str, desc: str, perms: list) -> bool:
        """Fuegt einen benutzerdefinierten Skill hinzu."""
        if key in self.SKILLS and self.SKILLS[key].get("builtin", True):
            return False  # Builtin Skills nicht ueberschreiben
        self.SKILLS[key] = {"name": name, "desc": desc, "perms": perms, "builtin": False}
        self._save_custom_skills()
        return True

    def delete_skill(self, key: str) -> bool:
        """Loescht einen benutzerdefinierten Skill."""
        if key not in self.SKILLS:
            return False
        if self.SKILLS[key].get("builtin", True):
            return False  # Builtin Skills nicht loeschbar
        del self.SKILLS[key]
        self._save_custom_skills()
        return True

    def export_skills(self, path: Path) -> bool:
        """Exportiert alle Skills als JSON."""
        try:
            data = self.get_all()
            path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception as e:
            print(f"[SkillManager] Export fehlgeschlagen: {e}")
            return False

    def import_skills(self, path: Path) -> tuple:
        """Importiert Skills aus JSON. Gibt (success_count, error_msg) zurueck."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            added = 0
            for key, info in data.items():
                if key not in self.SKILLS:
                    self.SKILLS[key] = {**info, "builtin": False}
                    added += 1
            self._save_custom_skills()
            return added, ""
        except Exception as e:
            return 0, str(e)
