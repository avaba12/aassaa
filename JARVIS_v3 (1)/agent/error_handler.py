"""Fehlerbehandlung mit Retry-Logik."""
from enum import Enum

class ErrorDecision(Enum):
    RETRY = "retry"
    SKIP = "skip"
    REPLAN = "replan"
    ABORT = "abort"

def analyze_error(step: dict, error: str, attempt: int = 1, max_attempts: int = 2) -> dict:
    if attempt >= max_attempts:
        return {"decision": ErrorDecision.REPLAN, "reason": f"Failed {attempt} times", "user_message": "Versuche alternativen Ansatz, Sir."}
    if "timeout" in error.lower() or "connection" in error.lower():
        return {"decision": ErrorDecision.RETRY, "reason": "Temporary error", "user_message": "Warte kurz, Sir."}
    if "not found" in error.lower() or "missing" in error.lower():
        return {"decision": ErrorDecision.SKIP, "reason": "Resource not found", "user_message": "Überspringe diesen Schritt, Sir."}
    return {"decision": ErrorDecision.RETRY, "reason": error[:100], "user_message": "Wiederhole, Sir."}

def generate_fix(step: dict, error: str, fix_suggestion: str) -> dict:
    return {
        "step": step.get("step"),
        "tool": "code_helper",
        "description": f"Auto-fix for: {step.get('description', '')}",
        "parameters": {"action": "run", "code": f"# Fix for: {fix_suggestion}"},
        "critical": step.get("critical", False)
    }
