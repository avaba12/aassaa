"""AI-Engine: Ollama mit Thinking/Reasoning Toggle."""
import json, time, re
from typing import Optional, Generator
from pathlib import Path
from memory.config_manager import ConfigManager
from memory.memory_manager import MemoryManager
from core.logger import get_logger
from core.skill_manager import SkillManager

logger = get_logger("AI")

class AIEngine:
    PROFILES = {
        "chat": {"name": "Chat", "desc": "Allgemeine Konversation", "default_model": "llama3"},
        "code": {"name": "Code", "desc": "Programmierung & Technik", "default_model": "codellama"},
        "vision": {"name": "Vision", "desc": "Bildanalyse", "default_model": "llava"},
    }

    def __init__(self):
        self.cfg = ConfigManager()
        self.memory = MemoryManager()
        self.skills = SkillManager()
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            import ollama
            host = self.cfg.get("ollama_host", "http://localhost:11434")
            self._client = ollama.Client(host=host)
            logger.info(f"Ollama-Client verbunden: {host}")
        except Exception as e:
            logger.warning(f"Ollama nicht verfuegbar: {e}")
            self._client = None

    def detect_profile(self, text: str) -> str:
        t = text.lower()
        code_keywords = ["python", "code", "programm", "script", "funktion", "klasse", "api", "debug", "error", "bug", "javascript", "html", "css", "sql", "c++", "java"]
        vision_keywords = ["bild", "image", "foto", "photo", "screenshot", "kamera", "camera", "sehe", "see", "erkenne", "erkennst"]
        if any(kw in t for kw in vision_keywords):
            return "vision"
        if any(kw in t for kw in code_keywords):
            return "code"
        return "chat"

    def get_model(self, profile: str) -> str:
        key = f"{profile}_model"
        model = self.cfg.get(key, self.PROFILES.get(profile, {}).get("default_model", "llama3"))
        return model

    def list_models(self):
        if not self._client:
            return []
        try:
            models = self._client.list()
            result = []
            for m in models.get("models", []):
                name = m.get("model", m.get("name", "unknown"))
                size = m.get("size", 0)
                size_mb = round(size / 1024 / 1024, 1)
                param = m.get("details", {}).get("parameter_size", "?")
                fam = m.get("details", {}).get("family", "?")
                result.append({
                    "name": name,
                    "size_mb": size_mb,
                    "parameters": param,
                    "family": fam,
                })
            return result
        except Exception as e:
            logger.error(f"Model list error: {e}")
            return []

    def install_model(self, name: str) -> str:
        try:
            logger.info(f"Lade Modell {name}...")
            import ollama
            host = self.cfg.get("ollama_host", "http://localhost:11434")
            client = ollama.Client(host=host)
            client.pull(name)
            return f"Modell '{name}' erfolgreich installiert."
        except Exception as e:
            return f"Fehler beim Installieren: {e}"

    def delete_model(self, name: str) -> str:
        try:
            self._client.delete(name)
            return f"Modell '{name}' geloescht."
        except Exception as e:
            return f"Fehler beim Loeschen: {e}"

    def chat(self, message: str, profile: Optional[str] = None, stream: bool = True) -> Generator[str, None, None]:
        if not self._client:
            yield "❌ Ollama ist nicht verbunden. Bitte starte Ollama (ollama.com)."
            return

        offline = self.cfg.get("offline_mode", True)
        prof = profile or self.detect_profile(message)
        model = self.get_model(prof)

        # Web-Suche immer aktiv
        context = ""
        if self.skills.is_enabled("web_search") and any(kw in message.lower() for kw in ["suche", "search", "finde", "google", "aktuell", "news", "nachrichten"]):
            try:
                from actions.web_search import web_search
                result = web_search({"query": message, "mode": "search"})
                context = f"\n\n[Web-Suche Ergebnisse]:\n{result[:2000]}"
            except Exception as e:
                logger.warning(f"Web search failed: {e}")

        # System-Prompt laden
        base_dir = Path(__file__).resolve().parent.parent
        prompt_file = base_dir / "core" / "prompt.txt"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else "You are J.A.R.V.I.S."
        system_prompt += f"\n\nUser name: {self.cfg.get('user_name', 'Sir')}"
        system_prompt += f"\nLanguage: {self.cfg.get('language', 'de-DE')}"
        if offline:
            system_prompt += "\n\n[OFFLINE MODE] Du laeufst komplett lokal. Kein Internet-Zugriff fuer TTS/STT."

        # Memory laden
        history = self.memory.get_history(limit=self.cfg.get("memory_limit", 100))
        messages = [{"role": "system", "content": system_prompt}]
        for h in history[-20:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message + context})

        self.memory.add("user", message, model=model)

        temp = self.cfg.get("temperature", 0.7)
        top_p = self.cfg.get("top_p", 0.9)

        # Thinking/Reasoning Einstellungen
        show_thinking = self.cfg.get("show_thinking", False)
        thinking_mode = self.cfg.get("thinking_mode", "instant")  # "thinking" oder "instant"

        start = time.time()
        full_response = []
        try:
            response = self._client.chat(
                model=model,
                messages=messages,
                stream=stream,
                options={"temperature": temp, "top_p": top_p}
            )
            if stream:
                thinking_buffer = ""
                in_think_tag = False
                for chunk in response:
                    text = chunk.get("message", {}).get("content", "")
                    if not text:
                        continue

                    # Thinking-Tag Parsing fuer Modelle wie deepseek-r1, qwq
                    if thinking_mode == "thinking" and show_thinking:
                        # Suche nach <thinking> oder  tags
                        if "<thinking>" in text or "<think>" in text or " reasoning" in text:
                            in_think_tag = True
                            thinking_buffer += text
                            # Sende Thinking-Text als speziellen Chunk
                            yield f"[THINK]{text}[/THINK]"
                            continue
                        elif "</thinking>" in text or "</think>" in text or "[/reasoning]" in text:
                            in_think_tag = False
                            thinking_buffer += text
                            yield f"[THINK]{text}[/THINK]"
                            continue
                        elif in_think_tag:
                            thinking_buffer += text
                            yield f"[THINK]{text}[/THINK]"
                            continue

                    full_response.append(text)
                    yield text
            else:
                text = response.get("message", {}).get("content", "")
                # Entferne Thinking-Tags wenn nicht gewünscht
                if thinking_mode == "instant":
                    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
                full_response.append(text)
                yield text

            complete = "".join(full_response)
            # Tags aus finaler Antwort entfernen für Memory
            clean_complete = re.sub(r'\[THINK\].*?\[/THINK\]', '', complete, flags=re.DOTALL)
            self.memory.add("assistant", clean_complete, model=model)
            elapsed = (time.time() - start) * 1000
            logger.info(f"⏱️  KI-Antwort: {elapsed:.0f}ms ({len(clean_complete)} chars)")

        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"❌ Fehler: {e}"

    def generate_code(self, description: str) -> str:
        model = self.get_model("code")
        try:
            response = self._client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert programmer. Write clean, working code."},
                    {"role": "user", "content": description}
                ],
                options={"temperature": 0.3}
            )
            return response.get("message", {}).get("content", "")
        except Exception as e:
            return f"Code generation failed: {e}"

    def analyze_image(self, image_path: str, question: str) -> str:
        model = self.get_model("vision")
        try:
            from PIL import Image
            import base64, io
            img = Image.open(image_path)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()

            response = self._client.chat(
                model=model,
                messages=[
                    {"role": "user", "content": question, "images": [b64]}
                ]
            )
            return response.get("message", {}).get("content", "")
        except Exception as e:
            return f"Image analysis failed: {e}"
