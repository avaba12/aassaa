"""Task-Planner für komplexe, mehrstufige Ziele."""
import json, re
from typing import List, Dict

def create_plan(goal: str) -> Dict:
    """Erstellt einen einfachen Plan basierend auf dem Ziel."""
    # Einfacher Keyword-basierter Planner
    goal_lower = goal.lower()
    steps = []

    if any(w in goal_lower for w in ["öffne", "open", "starte", "launch"]):
        app = _extract_app(goal)
        steps.append({"step": 1, "tool": "open_app", "description": f"Open {app}", "parameters": {"app_name": app}, "critical": False})

    if any(w in goal_lower for w in ["suche", "search", "finde", "google"]):
        query = _extract_query(goal)
        steps.append({"step": len(steps)+1, "tool": "web_search", "description": f"Search for {query}", "parameters": {"query": query}, "critical": False})

    if any(w in goal_lower for w in ["datei", "file", "ordner", "folder"]):
        steps.append({"step": len(steps)+1, "tool": "file_controller", "description": "File operation", "parameters": {"action": "list", "path": "desktop"}, "critical": False})

    if any(w in goal_lower for w in ["screenshot", "bildschirm", "screen"]):
        steps.append({"step": len(steps)+1, "tool": "screen_process", "description": "Capture screen", "parameters": {"text": "What do you see?"}, "critical": False})

    if not steps:
        steps.append({"step": 1, "tool": "generated_code", "description": f"Handle: {goal}", "parameters": {"description": goal}, "critical": True})

    return {"goal": goal, "steps": steps}

def replan(goal: str, completed: List[Dict], failed_step: Dict, error: str) -> Dict:
    """Erstellt einen neuen Plan nach einem Fehler."""
    plan = create_plan(goal)
    # Markiere bereits erledigte Schritte
    for step in plan["steps"]:
        if any(c.get("step") == step["step"] for c in completed):
            step["done"] = True
    return plan

def _extract_app(goal: str) -> str:
    words = goal.lower().split()
    apps = ["chrome", "firefox", "vscode", "notepad", "spotify", "discord", "telegram", "obsidian", "steam"]
    for app in apps:
        if app in words or app in goal.lower():
            return app
    return "notepad"

def _extract_query(goal: str) -> str:
    for prefix in ["suche nach", "search for", "finde", "google", "suche"]:
        if prefix in goal.lower():
            idx = goal.lower().index(prefix) + len(prefix)
            return goal[idx:].strip(" .!?")
    return goal
