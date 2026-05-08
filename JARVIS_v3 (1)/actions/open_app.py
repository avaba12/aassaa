import time, subprocess, platform, shutil

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_SYSTEM = platform.system()

_APP_ALIASES = {
    "chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "firefox": {"Windows": "firefox", "Darwin": "Firefox", "Linux": "firefox"},
    "edge": {"Windows": "msedge", "Darwin": "Microsoft Edge", "Linux": "microsoft-edge"},
    "brave": {"Windows": "brave", "Darwin": "Brave Browser", "Linux": "brave-browser"},
    "vscode": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "terminal": {"Windows": "wt", "Darwin": "Terminal", "Linux": "gnome-terminal"},
    "cmd": {"Windows": "cmd.exe", "Darwin": "Terminal", "Linux": "bash"},
    "powershell": {"Windows": "powershell.exe", "Darwin": "Terminal", "Linux": "bash"},
    "spotify": {"Windows": "Spotify", "Darwin": "Spotify", "Linux": "spotify"},
    "discord": {"Windows": "Discord", "Darwin": "Discord", "Linux": "discord"},
    "telegram": {"Windows": "Telegram", "Darwin": "Telegram", "Linux": "telegram"},
    "notepad": {"Windows": "notepad.exe", "Darwin": "TextEdit", "Linux": "gedit"},
    "explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "obsidian": {"Windows": "Obsidian", "Darwin": "Obsidian", "Linux": "obsidian"},
    "steam": {"Windows": "steam", "Darwin": "Steam", "Linux": "steam"},
}

def _normalize(raw: str) -> str:
    key = raw.lower().strip()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(_SYSTEM, raw)
    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(_SYSTEM, raw)
    return raw

def _launch_windows(app_name: str) -> bool:
    if shutil.which(app_name) or shutil.which(app_name.split(".")[0]):
        try:
            subprocess.Popen(app_name, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
            return True
        except Exception:
            pass
    if ":" in app_name:
        try:
            subprocess.Popen(f"start {app_name}", shell=True)
            time.sleep(1.0)
            return True
        except Exception:
            pass
    try:
        import pyautogui
        pyautogui.PAUSE = 0.1
        pyautogui.press("win")
        time.sleep(0.7)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.9)
        pyautogui.press("enter")
        time.sleep(2.5)
        return True
    except Exception:
        pass
    return False

def _launch_macos(app_name: str) -> bool:
    try:
        result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass
    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass
    return False

def _launch_linux(app_name: str) -> bool:
    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass
    return False

_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin": _launch_macos,
    "Linux": _launch_linux,
}

def open_app(parameters=None, response=None, player=None, session_memory=None) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()
    if not app_name:
        return "No application name provided."
    launcher = _OS_LAUNCHERS.get(_SYSTEM)
    if launcher is None:
        return f"Unsupported OS: {_SYSTEM}"
    normalized = _normalize(app_name)
    print(f"[open_app] Launching: '{app_name}' -> '{normalized}' ({_SYSTEM})")
    if player:
        player.write_log(f"[open_app] {app_name}")
    try:
        if launcher(normalized):
            return f"Opened {app_name}."
        if normalized.lower() != app_name.lower():
            if launcher(app_name):
                return f"Opened {app_name}."
        return f"Could not confirm that {app_name} launched."
    except Exception as e:
        return f"Failed to open {app_name}: {e}"
