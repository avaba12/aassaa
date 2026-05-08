import subprocess, sys, tempfile, os
from pathlib import Path

def code_helper(parameters=None, response=None, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    code = params.get("code", "")
    if player:
        player.write_log(f"[Code] {action}")
    if action == "run" and code:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            result = subprocess.run([sys.executable, tmp], capture_output=True, text=True, timeout=30)
            os.unlink(tmp)
            if result.returncode == 0:
                return result.stdout or "Code executed successfully."
            return f"Error: {result.stderr[:500]}"
        except Exception as e:
            return f"Code execution failed: {e}"
    return "No code provided."
