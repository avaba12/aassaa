import os, shutil, platform
from pathlib import Path
from datetime import datetime

try:
    import send2trash
    _SEND2TRASH = True
except ImportError:
    _SEND2TRASH = False

_OS = platform.system()
_SAFE_ROOTS = [Path.home()]

def _is_safe_path(target: Path) -> bool:
    try:
        resolved = target.resolve()
        return any(resolved == root.resolve() or resolved.is_relative_to(root.resolve()) for root in _SAFE_ROOTS)
    except Exception:
        return False

def _resolve_path(raw: str) -> Path:
    shortcuts = {
        "desktop": Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "home": Path.home(),
    }
    lower = raw.strip().lower()
    if lower in shortcuts:
        return shortcuts[lower]
    return Path(raw).expanduser()

def _format_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

def file_controller(parameters=None, response=None, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    path = params.get("path", "desktop")
    name = params.get("name", "")
    if player:
        player.write_log(f"[file] {action} {name or path}")
    try:
        if action == "list":
            target = _resolve_path(path)
            if not _is_safe_path(target): return f"Access denied: {target}"
            items = []
            for item in sorted(target.iterdir()):
                if item.is_dir(): items.append(f"📁 {item.name}/")
                else: items.append(f"📄 {item.name} ({_format_size(item.stat().st_size)})")
            return f"Contents of {target.name}/ ({len(items)} items):\n" + "\n".join(items) if items else "Empty."
        elif action == "read":
            target = _resolve_path(path) / name if name else _resolve_path(path)
            if not _is_safe_path(target): return f"Access denied: {target}"
            content = target.read_text(encoding="utf-8", errors="ignore")
            return content[:4000] + ("\n\n[Truncated]" if len(content) > 4000 else "")
        elif action == "create_file":
            target = _resolve_path(path) / name if name else _resolve_path(path)
            if not _is_safe_path(target): return f"Access denied: {target}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(params.get("content", ""), encoding="utf-8")
            return f"File created: {target.name}"
        elif action == "delete":
            target = _resolve_path(path) / name if name else _resolve_path(path)
            if not _is_safe_path(target): return f"Access denied: {target}"
            if _SEND2TRASH:
                send2trash.send2trash(str(target))
                return f"Moved to trash: {target.name}"
            return "send2trash not installed — deletion disabled for safety."
        elif action == "find":
            search_path = _resolve_path(path)
            if not _is_safe_path(search_path): return f"Access denied"
            results = []
            for item in search_path.rglob("*"):
                if item.is_file() and name.lower() in item.name.lower():
                    results.append(f"📄 {item.name} ({_format_size(item.stat().st_size)}) — {item.parent}")
                if len(results) >= 20: break
            return f"Found {len(results)} file(s):\n" + "\n".join(results) if results else "No files found."
        else:
            return f"Unknown action: '{action}'"
    except Exception as e:
        return f"File error ({action}): {e}"
