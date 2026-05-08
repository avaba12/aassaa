"""J.A.R.V.I.S PyQt6 UI — Hauptfenster mit Markdown, Thinking, Skills, Shortcuts."""
import sys, json, time
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame,
    QTabWidget, QSlider, QComboBox, QCheckBox, QSpinBox, QGroupBox,
    QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QDialog,
    QDialogButtonBox, QGridLayout, QInputDialog, QScrollArea,
    QProgressDialog, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QAction, QKeyEvent

from memory.config_manager import ConfigManager
from memory.memory_manager import MemoryManager
from core.ai_engine import AIEngine
from core.voice.engine import TTSEngine
from core.stt.listener import STTListener
from core.gpu_monitor import GPUMonitor
from core.skill_manager import SkillManager
from core.security import SecurityManager
from core.logger import get_logger
from agent.executor import AgentExecutor

logger = get_logger("UI")


class ModelScannerThread(QThread):
    models_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            import ollama
            cfg = ConfigManager()
            host = cfg.get("ollama_host", "http://localhost:11434")
            client = ollama.Client(host=host)
            models = client.list()
            result = []
            for m in models.get("models", []):
                name = m.get("model", m.get("name", "unknown"))
                size = m.get("size", 0)
                size_mb = round(size / 1024 / 1024, 1)
                param = m.get("details", {}).get("parameter_size", "?")
                fam = m.get("details", {}).get("family", "?")
                result.append({
                    "name": name,
                    "display": f"{name}  ({size_mb} MB, {param}, {fam})",
                    "size_mb": size_mb,
                    "parameters": param,
                    "family": fam,
                })
            self.models_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ChatWorker(QThread):
    text_ready = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, ai, message, profile="chat"):
        super().__init__()
        self.ai = ai
        self.message = message
        self.profile = profile
        self._running = True

    def run(self):
        try:
            for chunk in self.ai.chat(self.message, profile=self.profile, stream=True):
                if not self._running:
                    break
                self.text_ready.emit(chunk)
        except Exception as e:
            self.text_ready.emit(f"\n❌ Fehler: {e}")
        self.finished_signal.emit()

    def stop(self):
        self._running = False


class JARVISWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = ConfigManager()
        self.memory = MemoryManager()
        self.ai = AIEngine()
        self.tts = TTSEngine()
        self.stt = STTListener()
        self.gpu = GPUMonitor()
        self.skills = SkillManager()
        self.security = SecurityManager()
        self.executor = AgentExecutor()
        self.chat_worker = None
        self._current_response = []
        self._last_user_message = ""
        self._last_profile = "chat"
        self._setup_ui()
        self._setup_timers()
        self._setup_stt()
        self.apply_theme()
        self._show_offline_notice()

    def _setup_ui(self):
        self.setWindowTitle("J.A.R.V.I.S v3.0")
        self.setMinimumSize(1300, 850)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # SIDEBAR
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setSpacing(12)
        sb_layout.setContentsMargins(15, 20, 15, 20)

        title = QLabel("J.A.R.V.I.S")
        title.setObjectName("sidebarTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_layout.addWidget(title)

        self.offline_label = QLabel("🔒 OFFLINE MODUS")
        self.offline_label.setObjectName("offlineLabel")
        self.offline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_layout.addWidget(self.offline_label)

        self.status_label = QLabel("● System Online")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_layout.addWidget(self.status_label)

        sb_layout.addSpacing(15)

        gpu_group = QGroupBox("🎮 GPU Monitor")
        gpu_layout = QVBoxLayout(gpu_group)
        self.gpu_name = QLabel("GPU: Detecting...")
        self.gpu_vram = QLabel("VRAM: -- / --")
        self.gpu_temp = QLabel("Temp: --°C")
        self.gpu_load = QLabel("Load: --%")
        for w in [self.gpu_name, self.gpu_vram, self.gpu_temp, self.gpu_load]:
            gpu_layout.addWidget(w)
        self.btn_clear_vram = QPushButton("🧹 VRAM leeren")
        self.btn_clear_vram.clicked.connect(self._clear_vram)
        gpu_layout.addWidget(self.btn_clear_vram)
        sb_layout.addWidget(gpu_group)

        mem_group = QGroupBox("🧠 Memory")
        mem_layout = QVBoxLayout(mem_group)
        self.mem_entries = QLabel("Einträge: --")
        self.mem_size = QLabel("Größe: -- MB")
        self.btn_cleanup = QPushButton("🧹 Bereinigen")
        self.btn_cleanup.clicked.connect(self._cleanup_memory)
        for w in [self.mem_entries, self.mem_size, self.btn_cleanup]:
            mem_layout.addWidget(w)
        sb_layout.addWidget(mem_group)

        self.btn_mute = QPushButton("🎙️ Mikrofon: AN")
        self.btn_mute.setCheckable(True)
        self.btn_mute.clicked.connect(self._toggle_mute)
        sb_layout.addWidget(self.btn_mute)

        self.btn_tts_test = QPushButton("🔊 Test-Stimme")
        self.btn_tts_test.clicked.connect(self._test_tts)
        sb_layout.addWidget(self.btn_tts_test)

        sb_layout.addStretch()

        self.btn_settings = QPushButton("⚙️ Einstellungen")
        self.btn_settings.clicked.connect(self._open_settings)
        sb_layout.addWidget(self.btn_settings)

        layout.addWidget(sidebar)

        # MAIN
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("J.A.R.V.I.S bereit...")
        main_layout.addWidget(self.chat_display, stretch=1)

        self.typing_label = QLabel("")
        self.typing_label.setObjectName("typingLabel")
        main_layout.addWidget(self.typing_label)

        # Button-Leiste unter Chat
        btn_bar = QHBoxLayout()
        self.btn_regenerate = QPushButton("🔄 Nochmal generieren")
        self.btn_regenerate.clicked.connect(self._regenerate_last)
        self.btn_regenerate.setEnabled(False)
        btn_bar.addWidget(self.btn_regenerate)
        btn_bar.addStretch()
        main_layout.addLayout(btn_bar)

        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setSpacing(10)
        input_layout.setContentsMargins(15, 10, 15, 10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Befehl eingeben... (Ctrl+Enter zum Senden)")
        self.input_field.returnPressed.connect(self._send_message)
        self.input_field.setMinimumHeight(42)
        input_layout.addWidget(self.input_field, stretch=1)

        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(50, 42)
        self.btn_send.clicked.connect(self._send_message)
        input_layout.addWidget(self.btn_send)

        self.btn_voice = QPushButton("🎤")
        self.btn_voice.setFixedSize(50, 42)
        self.btn_voice.setCheckable(True)
        self.btn_voice.clicked.connect(self._toggle_voice)
        input_layout.addWidget(self.btn_voice)

        main_layout.addWidget(input_frame)
        layout.addWidget(main, stretch=1)

        # Menü
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Datei")
        file_menu.addAction("Export Chat", self._export_chat)
        file_menu.addAction("Import Chat", self._import_chat)
        file_menu.addSeparator()
        file_menu.addAction("Beenden", self.close)

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Model-Manager", self._open_model_manager)
        tools_menu.addAction("Plugin-Manager", self._open_plugin_manager)
        tools_menu.addAction("Audit-Log", self._open_audit_log)

        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("J.A.R.V.I.S")
        self.tray.activated.connect(self._tray_activated)
        tray_menu = QMenu()
        tray_menu.addAction("Öffnen", self.showNormal)
        tray_menu.addAction("Beenden", self.close)
        self.tray.setContextMenu(tray_menu)
        self.tray.show()

    def keyPressEvent(self, event):
        # Keyboard Shortcuts
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Return:
            self._send_message()
        elif event.key() == Qt.Key.Key_Escape:
            if self.isActiveWindow():
                self.input_field.setFocus()
        else:
            super().keyPressEvent(event)

    def _show_offline_notice(self):
        if self.cfg.get("offline_mode", True):
            self._append_chat("J.A.R.V.I.S", "🔒 Offline-Modus aktiv. Alle Funktionen laufen lokal. Web-Suche ist aktiv. Gehe zu Einstellungen > KI um auf Online-Modus zu wechseln.", "system")

    def _setup_timers(self):
        self.timer_gpu = QTimer()
        self.timer_gpu.timeout.connect(self._update_gpu)
        self.timer_gpu.start(3000)
        self._update_gpu()

        self.timer_mem = QTimer()
        self.timer_mem.timeout.connect(self._update_memory)
        self.timer_mem.start(5000)
        self._update_memory()

        self.timer_session = QTimer()
        self.timer_session.timeout.connect(self._check_session)
        self.timer_session.start(60000)

    def _setup_stt(self):
        def on_text(text):
            self.input_field.setText(text)
            self._send_message()
        def on_wake():
            self.tts.speak("Ja, Sir?")
            self.status_label.setText("● Hört zu...")
        self.stt.start(on_text=on_text, on_wake=on_wake)

    def apply_theme(self):
        theme = self.cfg.get("theme", "dark")
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow { background: #0a0a0a; }
                #sidebar { background: #111; border-right: 1px solid #222; }
                #sidebarTitle { color: #00ff88; font-size: 20px; font-weight: bold; }
                #statusLabel { color: #00ff88; font-size: 12px; }
                #offlineLabel { color: #ffaa00; font-size: 11px; font-weight: bold; background: #221a00; padding: 4px; border-radius: 4px; }
                #chatDisplay { background: #0f0f0f; color: #e0e0e0; border: 1px solid #222; border-radius: 8px; padding: 10px; font-size: 14px; }
                #inputFrame { background: #151515; border: 1px solid #222; border-radius: 8px; }
                QLineEdit { background: #1a1a1a; color: #e0e0e0; border: 1px solid #333; border-radius: 6px; padding: 5px 10px; font-size: 14px; }
                QPushButton { background: #1a3a2a; color: #00ff88; border: 1px solid #00ff88; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
                QPushButton:hover { background: #2a5a4a; }
                QPushButton:pressed { background: #1a3a2a; }
                QPushButton:checked { background: #3a1a1a; color: #ff4444; border-color: #ff4444; }
                QPushButton:disabled { background: #222; color: #555; border-color: #333; }
                QGroupBox { color: #00ff88; border: 1px solid #222; border-radius: 6px; margin-top: 10px; font-weight: bold; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QLabel { color: #ccc; font-size: 12px; }
                QComboBox { background: #1a1a1a; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; padding: 5px; min-height: 28px; }
                QComboBox::drop-down { border: none; }
                QComboBox QAbstractItemView { background: #1a1a1a; color: #e0e0e0; selection-background-color: #1a3a2a; }
                QSlider::groove:horizontal { background: #222; height: 6px; border-radius: 3px; }
                QSlider::handle:horizontal { background: #00ff88; width: 16px; height: 16px; border-radius: 8px; }
                QSpinBox { background: #1a1a1a; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; padding: 4px; }
                QCheckBox { color: #ccc; }
                QCheckBox::indicator { width: 18px; height: 18px; }
                QTextEdit { background: #0f0f0f; color: #e0e0e0; border: 1px solid #222; }
                #typingLabel { color: #888; font-style: italic; }
                QTabWidget::pane { border: 1px solid #222; background: #0f0f0f; }
                QTabBar::tab { background: #1a1a1a; color: #888; padding: 8px 16px; border: 1px solid #222; }
                QTabBar::tab:selected { background: #1a3a2a; color: #00ff88; }
                QMenuBar { background: #111; color: #ccc; }
                QMenuBar::item:selected { background: #1a3a2a; }
                QMenu { background: #151515; color: #ccc; border: 1px solid #222; }
                QMenu::item:selected { background: #1a3a2a; }
            """)
        else:
            self.setStyleSheet("")

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._last_user_message = text
        self._append_chat("Sie", text, "user")
        self.typing_label.setText("J.A.R.V.I.S schreibt...")
        self.btn_regenerate.setEnabled(False)

        if self.security.require_confirmation(text):
            reply = QMessageBox.question(self, "🛡️ Bestätigung erforderlich",
                f"Möchtest du wirklich:\n\n{text}\n\nDies könnte Daten verändern oder löschen.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                self._append_chat("J.A.R.V.I.S", "Aktion abgebrochen, Sir.", "assistant")
                self.typing_label.setText("")
                return

        profile = self.ai.detect_profile(text)
        self._last_profile = profile
        self._current_response = []
        self.chat_worker = ChatWorker(self.ai, text, profile)
        self.chat_worker.text_ready.connect(self._on_chat_chunk)
        self.chat_worker.finished_signal.connect(self._on_chat_done)
        self.chat_worker.start()

    def _regenerate_last(self):
        if not self._last_user_message:
            return
        self._append_chat("Sie", self._last_user_message + " [🔄 Neu generiert]", "user")
        self.typing_label.setText("J.A.R.V.I.S schreibt...")
        self._current_response = []
        self.chat_worker = ChatWorker(self.ai, self._last_user_message, self._last_profile)
        self.chat_worker.text_ready.connect(self._on_chat_chunk)
        self.chat_worker.finished_signal.connect(self._on_chat_done)
        self.chat_worker.start()

    def _on_chat_chunk(self, chunk):
        self._current_response.append(chunk)
        # Echtzeit-Anzeige für Thinking-Tags
        if "[THINK]" in chunk:
            think_text = chunk.replace("[THINK]", "").replace("[/THINK]", "")
            self.chat_display.append(f'<p><i style="color:#888">🧠 J.A.R.V.I.S denkt: {think_text}</i></p>')
        else:
            # Für Streaming: wir sammeln und zeigen am Ende (Markdown)
            pass

    def _on_chat_done(self):
        self.typing_label.setText("")
        self.btn_regenerate.setEnabled(True)
        full = "".join(self._current_response)
        # Entferne Thinking-Tags für finale Anzeige
        clean = full.replace("[THINK]", "").replace("[/THINK]", "")
        # Einfaches Markdown zu HTML
        html = self._markdown_to_html(clean)
        self._append_chat("J.A.R.V.I.S", html, "assistant", is_html=True)
        if self.cfg.get("tts_engine", "piper") != "none":
            self.tts.speak(clean[:500])
        self._current_response = []

    def _markdown_to_html(self, text):
        """Einfacher Markdown zu HTML Konverter."""
        import re
        # Code-Blöcke
        text = re.sub(r'```(\w+)?\n(.*?)```', r'<pre style="background:#1a1a1a;padding:10px;border-radius:6px;overflow-x:auto"><code>\2</code></pre>', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'<code style="background:#1a1a1a;padding:2px 4px;border-radius:3px">\1</code>', text)
        # Fett und kursiv
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        # Listen
        lines = text.split("\n")
        result = []
        in_list = False
        for line in lines:
            if line.strip().startswith("- "):
                if not in_list:
                    result.append("<ul>")
                    in_list = True
                result.append(f"<li>{line.strip()[2:]}</li>")
            else:
                if in_list:
                    result.append("</ul>")
                    in_list = False
                result.append(line)
        if in_list:
            result.append("</ul>")
        return "<br>".join(result)

    def _append_chat(self, sender, text, role, is_html=False):
        colors = {"user": "#4fc3f7", "assistant": "#00ff88", "system": "#ffaa00"}
        color = colors.get(role, "#e0e0e0")
        if is_html:
            html = f'<p><b style="color:{color}">{sender}:</b></p><div style="color:#e0e0e0">{text}</div>'
        else:
            html = f'<p><b style="color:{color}">{sender}:</b> <span style="color:#e0e0e0">{text}</span></p>'
        self.chat_display.append(html)

    def _update_gpu(self):
        try:
            info = self.gpu.get_info()
            self.gpu_name.setText(f"GPU: {info.get('name', 'Unknown')[:35]}")
            total = info.get('vram_total_mb', 0)
            used = info.get('vram_used_mb', 0)
            self.gpu_vram.setText(f"VRAM: {used} / {total} MB")
            self.gpu_temp.setText(f"Temp: {info.get('temperature_c', 0)}°C")
            self.gpu_load.setText(f"Load: {info.get('load_percent', 0)}%")
        except Exception:
            pass

    def _update_memory(self):
        try:
            stats = self.memory.get_stats()
            self.mem_entries.setText(f"Einträge: {stats.get('entries', 0)}")
            self.mem_size.setText(f"Größe: {stats.get('size_mb', 0)} MB")
        except Exception:
            pass

    def _check_session(self):
        if not self.security.is_session_valid() and self.cfg.get("pin_enabled", False):
            self._show_pin_dialog()

    def _show_pin_dialog(self):
        pin, ok = QInputDialog.getText(self, "🔒 Sicherheit", "PIN eingeben:", echo=QLineEdit.EchoMode.Password)
        if ok and pin:
            if not self.security.check_pin(pin):
                QMessageBox.warning(self, "Fehler", "Falsche PIN!")
                self.close()

    def _clear_vram(self):
        result = self.gpu.clear_vram()
        self.tts.speak("V R A M geleert, Sir.")
        QMessageBox.information(self, "VRAM", result)

    def _cleanup_memory(self):
        reply = QMessageBox.question(self, "🧹 Memory bereinigen",
            "Alte Einträge löschen? Dies kann nicht rückgängig gemacht werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            deleted = self.memory.cleanup(keep=self.cfg.get("memory_limit", 1000))
            self.tts.speak(f"{deleted} Einträge entfernt, Sir.")
            self._update_memory()

    def _toggle_mute(self):
        muted = self.btn_mute.isChecked()
        self.stt.set_mute(muted)
        self.btn_mute.setText("🔇 Mikrofon: AUS" if muted else "🎙️ Mikrofon: AN")

    def _toggle_voice(self):
        if self.btn_voice.isChecked():
            self.tts.speak("Spracheingabe aktiviert, Sir.")
        else:
            self.tts.speak("Spracheingabe deaktiviert, Sir.")

    def _test_tts(self):
        # Auto-Download Piper wenn nicht da
        piper_exe = Path("models/piper/piper.exe")
        if not piper_exe.exists() and self.cfg.get("tts_engine") == "piper":
            reply = QMessageBox.question(self, "📥 Piper TTS nicht gefunden",
                "Piper TTS ist nicht installiert.\n\nSoll ich es jetzt herunterladen? (~70MB)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._download_piper()
                return
        self.tts.speak("Hallo, ich bin J.A.R.V.I.S. Wie kann ich dir helfen, Sir?")

    def _download_piper(self):
        """Download Piper TTS mit Fortschrittsdialog."""
        dlg = QProgressDialog("Lade Piper TTS...", "Abbrechen", 0, 100, self)
        dlg.setWindowTitle("📥 Download")
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.show()

        import subprocess
        proc = subprocess.Popen([sys.executable, "setup_piper.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while proc.poll() is None:
            QApplication.processEvents()
            time.sleep(0.1)
        dlg.close()

        if proc.returncode == 0:
            QMessageBox.information(self, "✅ Fertig", "Piper TTS wurde installiert!")
            self.tts._check_piper_once()
        else:
            QMessageBox.warning(self, "⚠️ Fehler", "Piper-Download fehlgeschlagen. Verwende pyttsx3.")

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_offline_status()

    def _refresh_offline_status(self):
        offline = self.cfg.get("offline_mode", True)
        if offline:
            self.offline_label.setText("🔒 OFFLINE MODUS")
        else:
            self.offline_label.setText("🌐 ONLINE MODUS")

    def _open_model_manager(self):
        dlg = ModelManagerDialog(self.ai, self)
        dlg.exec()

    def _open_plugin_manager(self):
        QMessageBox.information(self, "Plugins", "Plugin-Manager — ziehe .py Dateien in den plugins/ Ordner.")

    def _open_audit_log(self):
        QMessageBox.information(self, "Audit", "Audit-Log wird in data/memory.db gespeichert.")

    def _export_chat(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Chat", "jarvis_chat.json", "JSON (*.json)")
        if path:
            self.memory.export_json(Path(path))
            QMessageBox.information(self, "Export", f"Chat exportiert nach:\n{path}")

    def _import_chat(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Chat", "", "JSON (*.json)")
        if path:
            QMessageBox.information(self, "Import", "Import-Funktion wird implementiert.")

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    def closeEvent(self, event):
        self.stt.stop()
        self.tts.stop()
        if self.chat_worker and self.chat_worker.isRunning():
            self.chat_worker.stop()
            self.chat_worker.wait(2000)
        event.accept()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ J.A.R.V.I.S Einstellungen")
        self.setMinimumSize(750, 700)
        self.cfg = ConfigManager()
        self._scanned_models = []
        self._setup_ui()
        self._load_models()
        self._update_tts_voices()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # ========== KI TAB ==========
        ki_tab = QWidget()
        ki_layout = QVBoxLayout(ki_tab)
        ki_layout.setSpacing(15)

        mode_group = QGroupBox("🌐 Verbindungsmodus")
        mode_layout = QVBoxLayout(mode_group)
        self.offline_mode = QCheckBox("🔒 Offline-Modus (TTS/STT lokal)")
        self.offline_mode.setChecked(self.cfg.get("offline_mode", True))
        self.offline_mode.stateChanged.connect(self._on_offline_changed)
        mode_layout.addWidget(self.offline_mode)
        self.mode_info = QLabel("🔒 Offline: Piper/pyttsx3, Vosk, lokales Wake-Word\n🌐 Online: + Edge-TTS, Google-STT, Porcupine")
        self.mode_info.setWordWrap(True)
        mode_layout.addWidget(self.mode_info)
        ki_layout.addWidget(mode_group)

        # Thinking / Reasoning
        think_group = QGroupBox("🧠 Thinking / Reasoning")
        think_layout = QVBoxLayout(think_group)
        self.show_thinking = QCheckBox("Thinking-Prozess anzeigen (nur bei Modellen wie deepseek-r1, qwq)")
        self.show_thinking.setChecked(self.cfg.get("show_thinking", False))
        think_layout.addWidget(self.show_thinking)
        self.thinking_mode = QComboBox()
        self.thinking_mode.addItem("Instant — Nur finale Antwort", "instant")
        self.thinking_mode.addItem("Thinking — Zeige Denkprozess", "thinking")
        idx = self.thinking_mode.findData(self.cfg.get("thinking_mode", "instant"))
        if idx >= 0:
            self.thinking_mode.setCurrentIndex(idx)
        think_layout.addWidget(self.thinking_mode)
        ki_layout.addWidget(think_group)

        models_group = QGroupBox("🧠 Ollama Modelle (automatisch erkannt)")
        models_layout = QGridLayout(models_group)
        models_layout.setSpacing(10)
        models_layout.addWidget(QLabel("Chat-Modell:"), 0, 0)
        self.chat_model = QComboBox()
        self.chat_model.setMinimumWidth(300)
        models_layout.addWidget(self.chat_model, 0, 1)
        models_layout.addWidget(QLabel("Code-Modell:"), 1, 0)
        self.code_model = QComboBox()
        self.code_model.setMinimumWidth(300)
        models_layout.addWidget(self.code_model, 1, 1)
        models_layout.addWidget(QLabel("Vision-Modell:"), 2, 0)
        self.vision_model = QComboBox()
        self.vision_model.setMinimumWidth(300)
        models_layout.addWidget(self.vision_model, 2, 1)
        self.btn_scan_models = QPushButton("🔄 Modelle scannen")
        self.btn_scan_models.clicked.connect(self._load_models)
        models_layout.addWidget(self.btn_scan_models, 3, 0, 1, 2)
        self.model_status = QLabel("Klicke 'Modelle scannen' um verfuegbare Modelle zu laden.")
        self.model_status.setStyleSheet("color: #888;")
        models_layout.addWidget(self.model_status, 4, 0, 1, 2)
        ki_layout.addWidget(models_group)

        host_group = QGroupBox("🔌 Ollama Verbindung")
        host_layout = QGridLayout(host_group)
        host_layout.addWidget(QLabel("Host:"), 0, 0)
        self.ollama_host = QComboBox()
        self.ollama_host.setEditable(True)
        self.ollama_host.addItems(["http://localhost:11434", "http://127.0.0.1:11434"])
        self.ollama_host.setCurrentText(self.cfg.get("ollama_host", "http://localhost:11434"))
        host_layout.addWidget(self.ollama_host, 0, 1)
        ki_layout.addWidget(host_group)

        tts_group = QGroupBox("🎙️ Text-to-Speech")
        tts_layout = QGridLayout(tts_group)
        tts_layout.setSpacing(10)
        tts_layout.addWidget(QLabel("Engine:"), 0, 0)
        self.tts_engine = QComboBox()
        self.tts_engine.addItem("Piper TTS (Offline, natuerlich)", "piper")
        self.tts_engine.addItem("pyttsx3 (Offline, roboterhaft)", "pyttsx3")
        self.tts_engine.currentIndexChanged.connect(self._update_tts_voices)
        tts_layout.addWidget(self.tts_engine, 0, 1)
        tts_layout.addWidget(QLabel("Stimme:"), 1, 0)
        self.tts_voice = QComboBox()
        self.tts_voice.setMinimumWidth(250)
        tts_layout.addWidget(self.tts_voice, 1, 1)
        tts_layout.addWidget(QLabel("Geschwindigkeit:"), 2, 0)
        speed_layout = QHBoxLayout()
        self.tts_speed = QSlider(Qt.Orientation.Horizontal)
        self.tts_speed.setRange(50, 200)
        self.tts_speed.setValue(int(self.cfg.get("tts_speed", 1.0) * 100))
        self.tts_speed.valueChanged.connect(self._update_speed_label)
        speed_layout.addWidget(self.tts_speed)
        self.speed_label = QLabel("1.0x")
        self.speed_label.setFixedWidth(50)
        speed_layout.addWidget(self.speed_label)
        tts_layout.addLayout(speed_layout, 2, 1)
        tts_layout.addWidget(QLabel("Lautstärke:"), 3, 0)
        vol_layout = QHBoxLayout()
        self.tts_volume = QSlider(Qt.Orientation.Horizontal)
        self.tts_volume.setRange(0, 100)
        self.tts_volume.setValue(int(self.cfg.get("tts_volume", 0.9) * 100))
        self.tts_volume.valueChanged.connect(self._update_volume_label)
        vol_layout.addWidget(self.tts_volume)
        self.volume_label = QLabel("90%")
        self.volume_label.setFixedWidth(50)
        vol_layout.addWidget(self.volume_label)
        tts_layout.addLayout(vol_layout, 3, 1)
        ki_layout.addWidget(tts_group)

        wake_group = QGroupBox("🎤 Sprachsteuerung")
        wake_layout = QGridLayout(wake_group)
        wake_layout.setSpacing(10)
        wake_layout.addWidget(QLabel("Wake-Word:"), 0, 0)
        self.wake_word = QComboBox()
        self.wake_word.setEditable(True)
        self.wake_word.addItems(["jarvis", "computer", "hey jarvis", "assistant", "hey assistant"])
        self.wake_word.setCurrentText(self.cfg.get("wake_word", "jarvis"))
        wake_layout.addWidget(self.wake_word, 0, 1)
        wake_layout.addWidget(QLabel("Sleep-Word:"), 1, 0)
        self.sleep_word = QComboBox()
        self.sleep_word.setEditable(True)
        self.sleep_word.addItems(["danke schlaf", "schlaf ein", "pause", "ruhe"])
        self.sleep_word.setCurrentText(self.cfg.get("sleep_word", "danke schlaf"))
        wake_layout.addWidget(self.sleep_word, 1, 1)
        wake_layout.addWidget(QLabel("Sprache:"), 2, 0)
        self.language = QComboBox()
        self.language.addItem("Deutsch", "de-DE")
        self.language.addItem("English (US)", "en-US")
        self.language.addItem("English (UK)", "en-GB")
        self.language.addItem("Türkçe", "tr-TR")
        idx = self.language.findData(self.cfg.get("language", "de-DE"))
        if idx >= 0:
            self.language.setCurrentIndex(idx)
        wake_layout.addWidget(self.language, 2, 1)
        self.local_wake = QCheckBox("Lokales Wake-Word (kein Internet/Key nötig)")
        self.local_wake.setChecked(self.cfg.get("use_local_wake_word", True))
        wake_layout.addWidget(self.local_wake, 3, 0, 1, 2)
        ki_layout.addWidget(wake_group)
        ki_layout.addStretch()
        tabs.addTab(ki_tab, "🧠 KI")

        # ========== USER TAB ==========
        user_tab = QWidget()
        user_layout = QVBoxLayout(user_tab)
        user_layout.setSpacing(15)
        prof_group = QGroupBox("👤 Profil")
        prof_layout = QGridLayout(prof_group)
        prof_layout.setSpacing(10)
        prof_layout.addWidget(QLabel("Name:"), 0, 0)
        self.user_name = QLineEdit(self.cfg.get("user_name", "Sir"))
        prof_layout.addWidget(self.user_name, 0, 1)
        prof_layout.addWidget(QLabel("System-Prompt:"), 1, 0, Qt.AlignmentFlag.AlignTop)
        self.sys_prompt = QTextEdit()
        self.sys_prompt.setMaximumHeight(120)
        base_dir = Path(__file__).resolve().parent
        prompt_file = base_dir / "core" / "prompt.txt"
        if prompt_file.exists():
            self.sys_prompt.setPlainText(prompt_file.read_text(encoding="utf-8"))
        prof_layout.addWidget(self.sys_prompt, 1, 1)
        prof_layout.addWidget(QLabel("Temperature:"), 2, 0)
        temp_layout = QHBoxLayout()
        self.temperature = QSlider(Qt.Orientation.Horizontal)
        self.temperature.setRange(0, 200)
        self.temperature.setValue(int(self.cfg.get("temperature", 0.7) * 100))
        self.temperature.valueChanged.connect(self._update_temp_label)
        temp_layout.addWidget(self.temperature)
        self.temp_label = QLabel("0.7")
        self.temp_label.setFixedWidth(50)
        temp_layout.addWidget(self.temp_label)
        prof_layout.addLayout(temp_layout, 2, 1)
        prof_layout.addWidget(QLabel("Top-P:"), 3, 0)
        topp_layout = QHBoxLayout()
        self.top_p = QSlider(Qt.Orientation.Horizontal)
        self.top_p.setRange(0, 100)
        self.top_p.setValue(int(self.cfg.get("top_p", 0.9) * 100))
        self.top_p.valueChanged.connect(self._update_topp_label)
        topp_layout.addWidget(self.top_p)
        self.topp_label = QLabel("0.9")
        self.topp_label.setFixedWidth(50)
        topp_layout.addWidget(self.topp_label)
        prof_layout.addLayout(topp_layout, 3, 1)
        user_layout.addWidget(prof_group)
        user_layout.addStretch()
        tabs.addTab(user_tab, "👤 User")

        # ========== SICHERHEIT TAB ==========
        sec_tab = QWidget()
        sec_layout = QVBoxLayout(sec_tab)
        sec_layout.setSpacing(15)
        pin_group = QGroupBox("🔒 PIN & Session")
        pin_layout = QGridLayout(pin_group)
        pin_layout.setSpacing(10)
        pin_layout.addWidget(QLabel("PIN-Schutz:"), 0, 0)
        self.pin_enabled = QCheckBox("Aktivieren")
        self.pin_enabled.setChecked(self.cfg.get("pin_enabled", False))
        pin_layout.addWidget(self.pin_enabled, 0, 1)
        pin_layout.addWidget(QLabel("PIN (4-6 Zahlen):"), 1, 0)
        self.pin_code = QLineEdit()
        self.pin_code.setEchoMode(QLineEdit.EchoMode.Password)
        pin_layout.addWidget(self.pin_code, 1, 1)
        pin_layout.addWidget(QLabel("Session-Timeout:"), 2, 0)
        timeout_layout = QHBoxLayout()
        self.session_timeout = QSpinBox()
        self.session_timeout.setRange(1, 120)
        self.session_timeout.setValue(self.cfg.get("session_timeout", 30))
        timeout_layout.addWidget(self.session_timeout)
        timeout_layout.addWidget(QLabel("Minuten"))
        timeout_layout.addStretch()
        pin_layout.addLayout(timeout_layout, 2, 1)
        sec_layout.addWidget(pin_group)
        confirm_group = QGroupBox("🛡️ Bestätigungen")
        confirm_layout = QVBoxLayout(confirm_group)
        self.confirmation = QCheckBox("Für gefährliche Aktionen (Löschen, Formatieren, etc.)")
        self.confirmation.setChecked(self.cfg.get("confirmation_required", True))
        confirm_layout.addWidget(self.confirmation)
        sec_layout.addWidget(confirm_group)
        sec_layout.addStretch()
        tabs.addTab(sec_tab, "🔒 Sicherheit")

        # ========== SKILLS TAB ==========
        skills_tab = QWidget()
        skills_scroll = QScrollArea()
        skills_scroll.setWidgetResizable(True)
        skills_widget = QWidget()
        skills_layout = QVBoxLayout(skills_widget)
        skills_layout.setSpacing(10)

        self.skill_checks = {}
        skills_data = self.cfg.get("skills", {})
        for key, info in SkillManager.SKILLS.items():
            cb = QCheckBox(f"{info['name']} — {info['desc']}")
            cb.setChecked(skills_data.get(key, False))
            self.skill_checks[key] = cb
            skills_layout.addWidget(cb)

        # Skill Management Buttons
        skills_layout.addSpacing(10)
        skill_btn_layout = QHBoxLayout()
        btn_add_skill = QPushButton("➕ Skill hinzufügen")
        btn_add_skill.clicked.connect(self._add_skill_dialog)
        skill_btn_layout.addWidget(btn_add_skill)
        btn_del_skill = QPushButton("🗑️ Skill löschen")
        btn_del_skill.clicked.connect(self._delete_skill_dialog)
        skill_btn_layout.addWidget(btn_del_skill)
        btn_export_skills = QPushButton("📤 Exportieren")
        btn_export_skills.clicked.connect(self._export_skills)
        skill_btn_layout.addWidget(btn_export_skills)
        btn_import_skills = QPushButton("📥 Importieren")
        btn_import_skills.clicked.connect(self._import_skills)
        skill_btn_layout.addWidget(btn_import_skills)
        skills_layout.addLayout(skill_btn_layout)

        skills_layout.addSpacing(10)
        master_group = QGroupBox("👑 Master-Modus")
        master_layout = QVBoxLayout(master_group)
        self.master_mode = QComboBox()
        self.master_mode.addItem("Admin — Alles erlaubt", "admin")
        self.master_mode.addItem("Standard — Sichere Berechtigungen", "standard")
        self.master_mode.addItem("Gast — Nur Chat", "guest")
        idx = self.master_mode.findData(self.cfg.get("master_mode", "standard"))
        if idx >= 0:
            self.master_mode.setCurrentIndex(idx)
        master_layout.addWidget(self.master_mode)
        skills_layout.addWidget(master_group)

        skills_layout.addStretch()
        skills_scroll.setWidget(skills_widget)
        skills_tab_layout = QVBoxLayout(skills_tab)
        skills_tab_layout.addWidget(skills_scroll)
        tabs.addTab(skills_tab, "🛡️ Skills")

        # ========== MEMORY TAB ==========
        mem_tab = QWidget()
        mem_layout = QVBoxLayout(mem_tab)
        mem_layout.setSpacing(15)
        mem_group = QGroupBox("🧠 Memory-Einstellungen")
        mem_grid = QGridLayout(mem_group)
        mem_grid.setSpacing(10)
        mem_grid.addWidget(QLabel("Limit:"), 0, 0)
        limit_layout = QHBoxLayout()
        self.mem_limit = QSpinBox()
        self.mem_limit.setRange(0, 50000)
        self.mem_limit.setValue(self.cfg.get("memory_limit", 1000))
        self.mem_limit.setSpecialValueText("Unendlich")
        limit_layout.addWidget(self.mem_limit)
        limit_layout.addWidget(QLabel("Einträge (0 = Unendlich)"))
        limit_layout.addStretch()
        mem_grid.addLayout(limit_layout, 0, 1)
        mem_grid.addWidget(QLabel("Auto-Cleanup:"), 1, 0)
        self.auto_cleanup = QCheckBox("Automatisch alte Einträge löschen")
        self.auto_cleanup.setChecked(self.cfg.get("auto_cleanup", True))
        mem_grid.addWidget(self.auto_cleanup, 1, 1)
        mem_layout.addWidget(mem_group)
        mem_layout.addStretch()
        tabs.addTab(mem_tab, "🧠 Memory")

        # ========== UI TAB ==========
        ui_tab = QWidget()
        ui_layout = QVBoxLayout(ui_tab)
        ui_layout.setSpacing(15)
        theme_group = QGroupBox("🎨 Erscheinungsbild")
        theme_layout = QVBoxLayout(theme_group)
        self.theme = QComboBox()
        self.theme.addItem("Dark Mode (Cyberpunk)", "dark")
        self.theme.addItem("Light Mode", "light")
        idx = self.theme.findData(self.cfg.get("theme", "dark"))
        if idx >= 0:
            self.theme.setCurrentIndex(idx)
        theme_layout.addWidget(self.theme)
        ui_layout.addWidget(theme_group)
        ui_layout.addStretch()
        tabs.addTab(ui_tab, "🖥️ UI")

        # ========== INTEGRATIONEN TAB ==========
        int_tab = QWidget()
        int_layout = QVBoxLayout(int_tab)
        int_layout.setSpacing(15)
        keys_group = QGroupBox("🔑 API-Keys (nur fuer Online-Features)")
        keys_layout = QGridLayout(keys_group)
        keys_layout.setSpacing(10)
        keys_layout.addWidget(QLabel("Gemini API-Key:"), 0, 0)
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        keys_layout.addWidget(self.gemini_key, 0, 1)
        keys_layout.addWidget(QLabel("Telegram Bot Token:"), 1, 0)
        self.telegram_token = QLineEdit()
        self.telegram_token.setEchoMode(QLineEdit.EchoMode.Password)
        keys_layout.addWidget(self.telegram_token, 1, 1)
        keys_layout.addWidget(QLabel("Discord Webhook:"), 2, 0)
        self.discord_webhook = QLineEdit()
        self.discord_webhook.setEchoMode(QLineEdit.EchoMode.Password)
        keys_layout.addWidget(self.discord_webhook, 2, 1)
        int_layout.addWidget(keys_group)
        int_layout.addStretch()
        tabs.addTab(int_tab, "🔗 Integrationen")

        layout.addWidget(tabs)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_offline_changed()
        self._update_speed_label()
        self._update_volume_label()
        self._update_temp_label()
        self._update_topp_label()

    def _load_models(self):
        self.model_status.setText("⏳ Scanne Ollama-Modelle...")
        self.btn_scan_models.setEnabled(False)
        self.scanner = ModelScannerThread()
        self.scanner.models_ready.connect(self._on_models_scanned)
        self.scanner.error.connect(self._on_models_error)
        self.scanner.finished.connect(lambda: self.btn_scan_models.setEnabled(True))
        self.scanner.start()

    def _on_models_scanned(self, models):
        self._scanned_models = models
        self.chat_model.clear()
        self.code_model.clear()
        self.vision_model.clear()
        defaults = ["llama3", "codellama", "llava", "mistral", "phi3", "gemma"]
        all_names = set(defaults)
        for m in models:
            all_names.add(m["name"])
        for name in sorted(all_names):
            display = name
            for m in models:
                if m["name"] == name:
                    display = m["display"]
                    break
            self.chat_model.addItem(display, name)
            self.code_model.addItem(display, name)
            self.vision_model.addItem(display, name)
        self._set_combo_value(self.chat_model, self.cfg.get("chat_model", "llama3"))
        self._set_combo_value(self.code_model, self.cfg.get("code_model", "codellama"))
        self._set_combo_value(self.vision_model, self.cfg.get("vision_model", "llava"))
        self.model_status.setText(f"✅ {len(models)} Modell(e) gefunden.")

    def _on_models_error(self, error):
        self.model_status.setText(f"❌ Fehler: {error}")
        for name in ["llama3", "codellama", "llava", "mistral"]:
            self.chat_model.addItem(name, name)
            self.code_model.addItem(name, name)
            self.vision_model.addItem(name, name)
        self._set_combo_value(self.chat_model, self.cfg.get("chat_model", "llama3"))
        self._set_combo_value(self.code_model, self.cfg.get("code_model", "codellama"))
        self._set_combo_value(self.vision_model, self.cfg.get("vision_model", "llava"))

    def _set_combo_value(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value or combo.itemText(i).startswith(value):
                combo.setCurrentIndex(i)
                return
        combo.setCurrentText(value)

    def _update_tts_voices(self):
        engine = self.tts_engine.currentData() or self.tts_engine.currentText()
        self.tts_voice.clear()
        if engine == "piper":
            self.tts_voice.addItem("Thorsten (Deutsch, maennlich)", "thorsten-de-medium")
            self.tts_voice.addItem("Eva (Deutsch, weiblich)", "eva-de-medium")
        elif engine == "pyttsx3":
            try:
                import pyttsx3
                e = pyttsx3.init()
                for v in e.getProperty("voices"):
                    self.tts_voice.addItem(v.name, v.id)
            except Exception:
                self.tts_voice.addItem("Standard", "")
        elif engine == "edge":
            self.tts_voice.addItem("Seraphina (de-DE, weiblich)", "de-DE-SeraphinaNeural")
            self.tts_voice.addItem("Killian (de-DE, maennlich)", "de-DE-KillianNeural")
            self.tts_voice.addItem("Amala (de-DE, weiblich)", "de-DE-AmalaNeural")
        current = self.cfg.get("tts_voice", "")
        for i in range(self.tts_voice.count()):
            if self.tts_voice.itemData(i) == current:
                self.tts_voice.setCurrentIndex(i)
                return

    def _on_offline_changed(self):
        offline = self.offline_mode.isChecked()
        current_engine = self.tts_engine.currentData() or self.tts_engine.currentText()
        self.tts_engine.clear()
        self.tts_engine.addItem("Piper TTS (Offline, natuerlich)", "piper")
        self.tts_engine.addItem("pyttsx3 (Offline, roboterhaft)", "pyttsx3")
        if not offline:
            self.tts_engine.addItem("Edge-TTS (Online, sehr natuerlich)", "edge")
        for i in range(self.tts_engine.count()):
            if self.tts_engine.itemData(i) == current_engine:
                self.tts_engine.setCurrentIndex(i)
                break
        else:
            self.tts_engine.setCurrentIndex(0)
        self._update_tts_voices()

    def _update_speed_label(self):
        self.speed_label.setText(f"{self.tts_speed.value()/100:.1f}x")
    def _update_volume_label(self):
        self.volume_label.setText(f"{self.tts_volume.value()}%")
    def _update_temp_label(self):
        self.temp_label.setText(f"{self.temperature.value()/100:.1f}")
    def _update_topp_label(self):
        self.topp_label.setText(f"{self.top_p.value()/100:.1f}")

    def _add_skill_dialog(self):
        name, ok = QInputDialog.getText(self, "➕ Skill hinzufügen", "Skill-Name:")
        if ok and name:
            desc, ok2 = QInputDialog.getText(self, "➕ Skill hinzufügen", "Beschreibung:")
            if ok2:
                key = name.lower().replace(" ", "_")
                self.skills.add_skill(key, name, desc, ["read_files"])
                QMessageBox.information(self, "✅ Fertig", f"Skill '{name}' hinzugefuegt!")
                # Neu laden
                cb = QCheckBox(f"{name} — {desc}")
                cb.setChecked(True)
                self.skill_checks[key] = cb
                # Leider muessen wir den Dialog neu oeffnen fuer die Anzeige
                QMessageBox.information(self, "🔄 Neu laden", "Schliesse und oeffne Einstellungen neu um den Skill zu sehen.")

    def _delete_skill_dialog(self):
        custom = [k for k, v in SkillManager.SKILLS.items() if not v.get("builtin", True)]
        if not custom:
            QMessageBox.information(self, "Info", "Keine benutzerdefinierten Skills zum Loeschen.")
            return
        item, ok = QInputDialog.getItem(self, "🗑️ Skill löschen", "Waehle Skill:", custom, 0, False)
        if ok and item:
            if self.skills.delete_skill(item):
                QMessageBox.information(self, "✅ Fertig", f"Skill '{item}' geloescht!")
            else:
                QMessageBox.warning(self, "❌ Fehler", "Skill konnte nicht geloescht werden.")

    def _export_skills(self):
        path, _ = QFileDialog.getSaveFileName(self, "Skills exportieren", "jarvis_skills.json", "JSON (*.json)")
        if path:
            if self.skills.export_skills(Path(path)):
                QMessageBox.information(self, "✅ Fertig", f"Skills exportiert nach:\n{path}")
            else:
                QMessageBox.warning(self, "❌ Fehler", "Export fehlgeschlagen.")

    def _import_skills(self):
        path, _ = QFileDialog.getOpenFileName(self, "Skills importieren", "", "JSON (*.json)")
        if path:
            count, error = self.skills.import_skills(Path(path))
            if error:
                QMessageBox.warning(self, "❌ Fehler", f"Import fehlgeschlagen: {error}")
            else:
                QMessageBox.information(self, "✅ Fertig", f"{count} Skill(s) importiert!")

    def _save(self):
        self.cfg.set("offline_mode", self.offline_mode.isChecked())
        self.cfg.set("show_thinking", self.show_thinking.isChecked())
        self.cfg.set("thinking_mode", self.thinking_mode.currentData() or self.thinking_mode.currentText())
        self.cfg.set("chat_model", self.chat_model.currentData() or self.chat_model.currentText().split()[0])
        self.cfg.set("code_model", self.code_model.currentData() or self.code_model.currentText().split()[0])
        self.cfg.set("vision_model", self.vision_model.currentData() or self.vision_model.currentText().split()[0])
        self.cfg.set("ollama_host", self.ollama_host.currentText())
        self.cfg.set("tts_engine", self.tts_engine.currentData() or self.tts_engine.currentText())
        self.cfg.set("tts_voice", self.tts_voice.currentData() or self.tts_voice.currentText())
        self.cfg.set("tts_speed", self.tts_speed.value() / 100)
        self.cfg.set("tts_volume", self.tts_volume.value() / 100)
        self.cfg.set("wake_word", self.wake_word.currentText())
        self.cfg.set("sleep_word", self.sleep_word.currentText())
        self.cfg.set("language", self.language.currentData() or self.language.currentText())
        self.cfg.set("use_local_wake_word", self.local_wake.isChecked())
        self.cfg.set("user_name", self.user_name.text())
        self.cfg.set("temperature", self.temperature.value() / 100)
        self.cfg.set("top_p", self.top_p.value() / 100)
        self.cfg.set("pin_enabled", self.pin_enabled.isChecked())
        if self.pin_code.text():
            from core.security import SecurityManager
            SecurityManager().set_pin(self.pin_code.text())
        self.cfg.set("session_timeout", self.session_timeout.value())
        self.cfg.set("confirmation_required", self.confirmation.isChecked())
        for key, cb in self.skill_checks.items():
            self.cfg.set(f"skills.{key}", cb.isChecked())
        self.cfg.set("master_mode", self.master_mode.currentData() or self.master_mode.currentText())
        self.cfg.set("memory_limit", self.mem_limit.value())
        self.cfg.set("auto_cleanup", self.auto_cleanup.isChecked())
        self.cfg.set("theme", self.theme.currentData() or self.theme.currentText())
        if self.gemini_key.text():
            self.cfg.set_api_key("gemini_api_key", self.gemini_key.text())
        if self.telegram_token.text():
            self.cfg.set_api_key("telegram_bot_token", self.telegram_token.text())
        if self.discord_webhook.text():
            self.cfg.set_api_key("discord_webhook", self.discord_webhook.text())
        if self.parent():
            self.parent().apply_theme()
            self.parent()._refresh_offline_status()
        self.accept()


class ModelManagerDialog(QDialog):
    def __init__(self, ai, parent=None):
        super().__init__(parent)
        self.ai = ai
        self.setWindowTitle("🧠 Model-Manager")
        self.setMinimumSize(550, 450)
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.model_list = QTextEdit()
        self.model_list.setReadOnly(True)
        layout.addWidget(self.model_list)

        hl = QHBoxLayout()
        self.install_input = QComboBox()
        self.install_input.setEditable(True)
        self.install_input.addItems(["llama3", "codellama", "llava", "mistral", "phi3", "gemma", "mixtral", "deepseek-r1", "qwq", "qwen2.5"])
        self.install_input.setMinimumWidth(250)
        hl.addWidget(self.install_input)
        btn_install = QPushButton("⬇️ Installieren")
        btn_install.clicked.connect(self._install)
        hl.addWidget(btn_install)
        layout.addLayout(hl)

        hl2 = QHBoxLayout()
        self.delete_input = QComboBox()
        self.delete_input.setEditable(True)
        self.delete_input.setMinimumWidth(250)
        hl2.addWidget(self.delete_input)
        btn_delete = QPushButton("🗑️ Loeschen")
        btn_delete.clicked.connect(self._delete)
        hl2.addWidget(btn_delete)
        layout.addLayout(hl2)

        btn_refresh = QPushButton("🔄 Aktualisieren")
        btn_refresh.clicked.connect(self._refresh)
        layout.addWidget(btn_refresh)

    def _refresh(self):
        models = self.ai.list_models()
        lines = ["Installierte Modelle:", "=" * 50]
        self.delete_input.clear()
        for m in models:
            lines.append(f"• {m['name']} — {m['size_mb']} MB — {m['parameters']} — {m['family']}")
            self.delete_input.addItem(m['name'])
        self.model_list.setText("\n".join(lines) if models else "Keine Modelle gefunden. Ist Ollama gestartet?")

    def _install(self):
        name = self.install_input.currentText().strip()
        if not name:
            return
        reply = QMessageBox.question(self, "Bestaetigung", f"Modell '{name}' installieren?\nDas kann einige Minuten dauern.")
        if reply == QMessageBox.StandardButton.Yes:
            result = self.ai.install_model(name)
            QMessageBox.information(self, "Ergebnis", result)
            self._refresh()

    def _delete(self):
        name = self.delete_input.currentText().strip()
        if not name:
            return
        reply = QMessageBox.question(self, "🛡️ Bestaetigung", f"Modell '{name}' wirklich loeschen?\nVRAM wird freigegeben.")
        if reply == QMessageBox.StandardButton.Yes:
            result = self.ai.delete_model(name)
            QMessageBox.information(self, "Ergebnis", result)
            self._refresh()
