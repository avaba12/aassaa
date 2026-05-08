import io, json, re, subprocess, sys, time, random, string
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("pyautogui not installed")

def _type(text: str, interval: float = 0.03) -> str:
    _require_pyautogui()
    time.sleep(0.3)
    pyautogui.typewrite(text, interval=interval)
    return f"Typed: {text[:60]}{'...' if len(text) > 60 else ''}"

def _click(x=None, y=None, button: str = "left", clicks: int = 1) -> str:
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(x, y, button=button, clicks=clicks)
        return f"Clicked ({x}, {y}) [{button}]"
    pyautogui.click(button=button, clicks=clicks)
    return "Clicked at current position"

def _hotkey(*keys) -> str:
    _require_pyautogui()
    pyautogui.hotkey(*keys)
    return f"Hotkey: {'+'.join(keys)}"

def _screenshot(save_path: str = None) -> str:
    _require_pyautogui()
    path = Path(save_path) if save_path else Path.home() / "Desktop" / "jarvis_screenshot.png"
    img = pyautogui.screenshot()
    img.save(str(path))
    return f"Screenshot saved: {path}"

def computer_control(parameters=None, response=None, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    if not action:
        return "No action specified."
    if player:
        player.write_log(f"[Computer] {action}")
    try:
        if action == "type":
            return _type(params.get("text", ""))
        elif action == "click":
            return _click(params.get("x"), params.get("y"))
        elif action == "hotkey":
            keys = [k.strip() for k in params.get("keys", "").split("+")]
            return _hotkey(*keys)
        elif action == "screenshot":
            return _screenshot(params.get("path"))
        elif action == "press":
            _require_pyautogui()
            pyautogui.press(params.get("key", "enter"))
            return f"Pressed: {params.get('key')}"
        elif action == "scroll":
            _require_pyautogui()
            pyautogui.scroll(int(params.get("amount", 3)))
            return "Scrolled."
        elif action == "move":
            _require_pyautogui()
            pyautogui.moveTo(int(params.get("x", 0)), int(params.get("y", 0)))
            return f"Moved to ({params.get('x')}, {params.get('y')})"
        else:
            return f"Unknown action: '{action}'"
    except Exception as e:
        return f"computer_control '{action}' failed: {e}"
