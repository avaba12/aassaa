import subprocess, platform

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

_OS = platform.system()

def volume_up():
    if _OS == "Windows":
        for _ in range(5): pyautogui.press("volumeup")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"], capture_output=True)

def volume_down():
    if _OS == "Windows":
        for _ in range(5): pyautogui.press("volumedown")
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"], capture_output=True)

def volume_mute():
    if _OS == "Windows": pyautogui.press("volumemute")

def close_app():
    if _OS == "Darwin": pyautogui.hotkey("command", "q")
    else: pyautogui.hotkey("alt", "f4")

def switch_window():
    if _OS == "Darwin": pyautogui.hotkey("command", "tab")
    else: pyautogui.hotkey("alt", "tab")

def show_desktop():
    if _OS == "Windows": pyautogui.hotkey("win", "d")
    elif _OS == "Darwin": pyautogui.hotkey("fn", "f11")

def lock_screen():
    if _OS == "Windows": pyautogui.hotkey("win", "l")
    elif _OS == "Darwin": subprocess.run(["pmset", "displaysleepnow"], capture_output=True)

def screenshot():
    if _OS == "Windows": pyautogui.hotkey("win", "shift", "s")
    elif _OS == "Darwin": pyautogui.hotkey("command", "shift", "3")

ACTION_MAP = {
    "volume_up": volume_up, "volume_down": volume_down, "mute": volume_mute,
    "close_app": close_app, "switch_window": switch_window,
    "show_desktop": show_desktop, "lock_screen": lock_screen, "screenshot": screenshot,
}

def computer_settings(parameters=None, response=None, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    if not action:
        return "No action specified."
    if player:
        player.write_log(f"[Settings] {action}")
    func = ACTION_MAP.get(action)
    if not func:
        return f"Unknown action: '{action}'"
    try:
        func()
        return f"Done: {action}."
    except Exception as e:
        return f"Action failed ({action}): {e}"
