import subprocess, platform, shutil
from pathlib import Path

_OS = platform.system()

def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url: return "about:blank"
    if "://" in url: return url
    if "." not in url: url = url + ".com"
    return "https://" + url

def browser_control(parameters=None, response=None, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    url = params.get("url", "")
    if player:
        player.write_log(f"[Browser] {action} {url}")
    try:
        if action == "go_to":
            url = _normalize_url(url)
            if _OS == "Windows":
                subprocess.Popen(["start", url], shell=True)
            elif _OS == "Darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
            return f"Opened: {url}"
        elif action == "search":
            query = params.get("query", "")
            search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
            return browser_control({"action": "go_to", "url": search_url}, player=player)
        else:
            return f"Unknown browser action: '{action}'"
    except Exception as e:
        return f"Browser error: {e}"
