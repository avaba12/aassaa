"""Universal TTS-Engine: Piper (optional) → Edge-TTS → pyttsx3 (Fallback)."""
import os, sys, tempfile, asyncio, threading, queue, time
from pathlib import Path
from typing import Optional
from memory.config_manager import ConfigManager
from core.logger import get_logger

logger = get_logger("TTS")

class TTSEngine:
    def __init__(self):
        self.cfg = ConfigManager()
        self._lock = threading.Lock()
        self._audio_queue = queue.Queue()
        self._speaking = False
        self._stop_flag = threading.Event()
        self._thread = threading.Thread(target=self._player_loop, daemon=True)
        self._thread.start()
        self._pyttsx3_engine = None
        self._piper_available = None  # None = noch nicht geprüft
        self._init_pyttsx3()
        self._check_piper_once()

    def _check_piper_once(self):
        """Prüft Piper nur EINMAL beim Start."""
        if self._piper_available is not None:
            return
        piper_exe = self._find_piper()
        model_file = Path(self.cfg.get("piper_path", "models/piper")) / "thorsten-de-medium.onnx"
        self._piper_available = piper_exe is not None and model_file.exists()
        if self._piper_available:
            logger.info("Piper TTS verfügbar")
        else:
            logger.info("Piper TTS nicht verfügbar — verwende pyttsx3/Edge")

    def _init_pyttsx3(self):
        try:
            import pyttsx3
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", 180)
            logger.info("pyttsx3 initialisiert (OFFLINE)")
        except Exception as e:
            logger.warning(f"pyttsx3 nicht verfügbar: {e}")

    def _find_piper(self) -> Optional[Path]:
        piper_dir = Path(self.cfg.get("piper_path", "models/piper"))
        exe = piper_dir / "piper.exe"
        if exe.exists():
            return exe
        for path in os.environ.get("PATH", "").split(os.pathsep):
            p = Path(path) / "piper.exe"
            if p.exists():
                return p
        return None

    def speak(self, text: str, engine_id: Optional[str] = None, voice_id: Optional[str] = None):
        if not text or not text.strip():
            return
        eid = engine_id or self.cfg.get("tts_engine", "piper")
        vid = voice_id or self.cfg.get("tts_voice", "")
        speed = self.cfg.get("tts_speed", 1.0)
        volume = self.cfg.get("tts_volume", 0.9)

        # Offline-Modus: Edge blockieren
        if self.cfg.get("offline_mode", True) and eid == "edge":
            eid = "piper" if self._piper_available else "pyttsx3"

        with self._lock:
            self._audio_queue.put((text, eid, vid, speed, volume))

    def _player_loop(self):
        while not self._stop_flag.is_set():
            try:
                text, eid, vid, speed, volume = self._audio_queue.get(timeout=0.5)
                self._speaking = True
                self._play(text, eid, vid, speed, volume)
                self._speaking = False
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS Player error: {e}")
                self._speaking = False

    def _play(self, text: str, eid: str, vid: str, speed: float, volume: float):
        # Offline-Modus: Piper → pyttsx3
        if self.cfg.get("offline_mode", True):
            if eid == "piper" and self._piper_available:
                if self._play_piper(text, vid, speed, volume):
                    return
            # Silent Fallback zu pyttsx3 (nur 1 Warning im Log)
            self._play_pyttsx3(text, speed, volume)
            return

        # Online-Modus: Piper → Edge → pyttsx3
        if eid == "piper" and self._piper_available:
            if self._play_piper(text, vid, speed, volume):
                return
        if eid in ("piper", "edge"):
            if self._play_edge(text, vid, speed, volume):
                return
        self._play_pyttsx3(text, speed, volume)

    def _play_piper(self, text: str, voice_id: str, speed: float, volume: float) -> bool:
        try:
            piper_exe = self._find_piper()
            if not piper_exe:
                return False
            model_dir = Path(self.cfg.get("piper_path", "models/piper"))
            model_file = model_dir / f"{voice_id}.onnx"
            if not model_file.exists():
                model_file = model_dir / "thorsten-de-medium.onnx"
            if not model_file.exists():
                return False

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                out_wav = f.name

            cmd = [
                str(piper_exe),
                "-m", str(model_file),
                "-f", out_wav,
                "--length_scale", str(1.0 / speed),
            ]
            import subprocess
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
            proc.communicate(input=text, timeout=30)
            proc.wait()

            if os.path.exists(out_wav) and os.path.getsize(out_wav) > 0:
                self._play_wav(out_wav, volume)
                os.unlink(out_wav)
                return True
            return False
        except Exception as e:
            logger.warning(f"Piper error: {e}")
            return False

    def _play_edge(self, text: str, voice_id: str, speed: float, volume: float) -> bool:
        if self.cfg.get("offline_mode", True):
            return False
        try:
            import edge_tts, asyncio
            voice = voice_id or "de-DE-SeraphinaNeural"
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                out_mp3 = f.name

            communicate = edge_tts.Communicate(text, voice, rate=f"{int((speed-1)*100)}%")
            asyncio.run(communicate.save(out_mp3))

            if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0:
                self._play_mp3(out_mp3, volume)
                os.unlink(out_mp3)
                return True
            return False
        except Exception as e:
            logger.warning(f"Edge-TTS error: {e}")
            return False

    def _play_pyttsx3(self, text: str, speed: float, volume: float):
        if not self._pyttsx3_engine:
            self._init_pyttsx3()
            if not self._pyttsx3_engine:
                logger.error("Kein TTS-Engine verfügbar!")
                return
        try:
            self._pyttsx3_engine.setProperty("rate", int(180 * speed))
            self._pyttsx3_engine.setProperty("volume", volume)
            voice_id = self.cfg.get("tts_voice", "")
            if voice_id:
                self._pyttsx3_engine.setProperty("voice", voice_id)
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 error: {e} — resette Engine")
            # Engine resetten bei Crash
            try:
                self._pyttsx3_engine.stop()
            except Exception:
                pass
            self._pyttsx3_engine = None
            self._init_pyttsx3()

    def _play_wav(self, path: str, volume: float = 1.0):
        try:
            import soundfile as sf
            import sounddevice as sd
            data, sr = sf.read(path, dtype="float32")
            data = data * volume
            sd.play(data, sr)
            sd.wait()
        except Exception as e:
            logger.warning(f"WAV play error: {e}")

    def _play_mp3(self, path: str, volume: float = 1.0):
        try:
            from pydub import AudioSegment
            import sounddevice as sd
            import numpy as np
            audio = AudioSegment.from_mp3(path)
            audio = audio + (20 * (volume - 1))
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
            samples = samples / (2**15)
            sd.play(samples, audio.frame_rate)
            sd.wait()
        except Exception:
            try:
                import subprocess
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path], timeout=60)
            except Exception:
                pass

    def stop(self):
        self._stop_flag.set()
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    @property
    def is_speaking(self) -> bool:
        return self._speaking
