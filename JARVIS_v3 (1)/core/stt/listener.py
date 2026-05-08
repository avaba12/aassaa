"""STT-Listener: Vosk (offline) → Google Speech (nur Online) + lokales Wake-Word ohne Key."""
import threading, queue, time, os, sys, struct, math
from pathlib import Path
from typing import Callable, Optional
from memory.config_manager import ConfigManager
from core.logger import get_logger

logger = get_logger("STT")

class STTListener:
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
        self.cfg = ConfigManager()
        self._running = False
        self._muted = False
        self._sleeping = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable] = None
        self._wake_callback: Optional[Callable] = None
        self._vosk_model = None
        self._porcupine = None
        self._recorder = None
        self._init_vosk()

    def _init_vosk(self):
        """Lade Vosk-Modell fuer offline STT."""
        try:
            from vosk import Model
            model_name = self.cfg.get("vosk_model", "vosk-model-small-de-0.15")
            model_path = Path("models") / model_name
            if model_path.exists():
                self._vosk_model = Model(str(model_path))
                logger.info(f"Vosk-Modell geladen: {model_name}")
            else:
                logger.warning(f"Vosk-Modell nicht gefunden: {model_path}")
                logger.info("Lade Vosk-Modell mit: python -m vosk --model {model_name}")
        except ImportError:
            logger.warning("Vosk nicht installiert — pip install vosk")
        except Exception as e:
            logger.warning(f"Vosk-Init fehlgeschlagen: {e}")

    def start(self, on_text: Callable[[str], None], on_wake: Optional[Callable] = None):
        self._callback = on_text
        self._wake_callback = on_wake
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="STTListener")
        self._thread.start()
        logger.info("STT-Listener gestartet")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("STT-Listener gestoppt")

    def set_mute(self, muted: bool):
        self._muted = muted
        logger.info(f"Mikrofon {'stumm' if muted else 'aktiv'}")

    @property
    def is_muted(self) -> bool:
        return self._muted

    @property
    def is_sleeping(self) -> bool:
        return self._sleeping

    def _listen_loop(self):
        """Hauptschleife: Wake-Word Erkennung -> STT."""
        offline = self.cfg.get("offline_mode", True)
        use_local_wake = self.cfg.get("use_local_wake_word", True)

        if use_local_wake:
            logger.info("Lokales Wake-Word aktiv — warte auf 'Jarvis'...")
            self._local_wake_word_loop()
        elif not offline:
            # Porcupine nur im Online-Modus
            self._porcupine_wake_word_loop()
        else:
            logger.info("Kein Wake-Word — verwende Push-to-Talk oder Texteingabe")

    def _local_wake_word_loop(self):
        """Lokales Wake-Word via Energie-Detektion + Vosk Keyword."""
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000,
                             input=True, frames_per_buffer=8000)
            wake_word = self.cfg.get("wake_word", "jarvis").lower()

            while self._running:
                if self._muted or self._sleeping:
                    time.sleep(0.5)
                    continue

                # Audio aufnehmen
                data = stream.read(8000, exception_on_overflow=False)
                # Energie berechnen
                energy = self._calculate_energy(data)
                if energy < 500:  # Schwellwert fuer Stimme
                    continue

                # Wenn Energie hoch → Vosk STT fuer Wake-Word-Pruefung
                text = self._recognize_vosk_chunk(data)
                if text and wake_word in text.lower():
                    logger.info(f"🔔 Wake-Word erkannt: '{text}'")
                    self._sleeping = False
                    if self._wake_callback:
                        self._wake_callback()
                    # Nach Wake-Word: auf Befehl hoeren
                    self._listen_command(stream)

            stream.stop_stream()
            stream.close()
            pa.terminate()
        except Exception as e:
            logger.error(f"Local wake-word error: {e}")
            # Fallback: einfache STT ohne Wake-Word
            self._simple_stt_loop()

    def _porcupine_wake_word_loop(self):
        """Porcupine Wake-Word (nur Online, braucht Key)."""
        try:
            import pvporcupine
            from pvrecorder import PvRecorder
            access_key = os.environ.get("PORCUPINE_ACCESS_KEY", "")
            if not access_key:
                logger.warning("PORCUPINE_ACCESS_KEY nicht gesetzt")
                self._simple_stt_loop()
                return
            wake_word = self.cfg.get("wake_word", "jarvis").lower()
            builtin = {"jarvis": "jarvis", "computer": "computer", "hey google": "hey google",
                       "alexa": "alexa", "ok google": "ok google", "hey siri": "hey siri"}
            if wake_word in builtin:
                self._porcupine = pvporcupine.create(access_key=access_key, keywords=[builtin[wake_word]])
            else:
                self._porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"])
            self._recorder = PvRecorder(frame_length=self._porcupine.frame_length, device_index=-1)
            self._recorder.start()
            while self._running:
                pcm = self._recorder.read()
                if self._porcupine.process(pcm) >= 0:
                    logger.info("🔔 Wake-Word erkannt!")
                    self._sleeping = False
                    if self._wake_callback:
                        self._wake_callback()
                    self._listen_for_speech(duration=5)
        except Exception as e:
            logger.warning(f"Porcupine nicht verfuegbar: {e}")
            self._simple_stt_loop()

    def _simple_stt_loop(self):
        """Einfache STT-Schleife ohne Wake-Word (Push-to-Talk aehnlich)."""
        logger.info("Einfache STT-Schleife (kein Wake-Word)")
        while self._running:
            if not self._muted and not self._sleeping:
                self._listen_for_speech(duration=3)
            time.sleep(0.5)

    def _listen_command(self, stream):
        """Hoert auf einen Befehl nach dem Wake-Word."""
        logger.info("Hoere auf Befehl...")
        try:
            import pyaudio
            frames = []
            for _ in range(20):  # ~2 Sekunden
                data = stream.read(1600, exception_on_overflow=False)
                frames.append(data)

            audio_data = b"".join(frames)
            text = self._recognize_vosk(audio_data)

            if text:
                logger.info(f"🎤 Befehl erkannt: {text}")
                # Sleep-Word pruefen
                sleep_word = self.cfg.get("sleep_word", "danke schlaf").lower()
                if sleep_word in text.lower():
                    logger.info("😴 Sleep-Word erkannt")
                    self._sleeping = True
                    return
                if self._callback:
                    self._callback(text)
        except Exception as e:
            logger.warning(f"Command listen error: {e}")

    def _listen_for_speech(self, duration: int = 5):
        """Nimmt Sprache auf und erkennt Text."""
        if self._muted:
            return
        offline = self.cfg.get("offline_mode", True)

        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000,
                             input=True, frames_per_buffer=1600)
            frames = []
            for _ in range(int(duration * 10)):
                data = stream.read(1600, exception_on_overflow=False)
                frames.append(data)
            stream.stop_stream()
            stream.close()
            pa.terminate()

            audio_data = b"".join(frames)

            # Offline: Vosk
            if offline and self._vosk_model:
                text = self._recognize_vosk(audio_data)
            elif not offline:
                # Online: Google Speech
                text = self._recognize_google(audio_data)
            else:
                text = None

            if text:
                logger.info(f"🎤 Erkannt: {text}")
                sleep_word = self.cfg.get("sleep_word", "danke schlaf").lower()
                if sleep_word in text.lower():
                    logger.info("😴 Sleep-Word erkannt")
                    self._sleeping = True
                    return
                if self._callback and text.strip():
                    self._callback(text)
        except Exception as e:
            logger.warning(f"STT error: {e}")

    def _recognize_vosk(self, audio_data: bytes) -> Optional[str]:
        """Erkennt Sprache mit Vosk (offline)."""
        if not self._vosk_model:
            return None
        try:
            from vosk import KaldiRecognizer
            rec = KaldiRecognizer(self._vosk_model, 16000)
            rec.AcceptWaveform(audio_data)
            result = rec.Result()
            import json
            data = json.loads(result)
            return data.get("text", "").strip() or None
        except Exception as e:
            logger.warning(f"Vosk error: {e}")
            return None

    def _recognize_vosk_chunk(self, audio_data: bytes) -> Optional[str]:
        """Erkennt Sprache mit Vosk fuer kleine Chunks."""
        return self._recognize_vosk(audio_data)

    def _recognize_google(self, audio_data: bytes) -> Optional[str]:
        """Erkennt Sprache mit Google (online, braucht Internet)."""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            audio = sr.AudioData(audio_data, 16000, 2)
            return r.recognize_google(audio, language=self.cfg.get("language", "de-DE"))
        except Exception:
            return None

    @staticmethod
    def _calculate_energy(data: bytes) -> float:
        """Berechnet die Audio-Energie fuer VAD."""
        count = len(data) // 2
        if count == 0:
            return 0.0
        format_str = "%dh" % count
        shorts = struct.unpack(format_str, data)
        sum_squares = sum(s * s for s in shorts)
        return math.sqrt(sum_squares / count)
