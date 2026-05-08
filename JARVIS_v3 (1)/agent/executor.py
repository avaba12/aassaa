"""Task-Executor führt Pläne Schritt für Schritt aus."""
import threading, time
from typing import Callable, Optional
from agent.planner import create_plan, replan
from core.logger import get_logger

logger = get_logger("Executor")

class AgentExecutor:
    MAX_REPLAN = 2

    def execute(self, goal: str, speak: Optional[Callable] = None, cancel_flag: Optional[threading.Event] = None) -> str:
        logger.info(f"🎯 Goal: {goal}")
        replan_attempts = 0
        plan = create_plan(goal)

        while True:
            steps = plan.get("steps", [])
            if not steps:
                msg = "Ich konnte keinen Plan erstellen, Sir."
                if speak: speak(msg)
                return msg

            success = True
            failed_step = None
            failed_error = ""

            for step in steps:
                if cancel_flag and cancel_flag.is_set():
                    if speak: speak("Aufgabe abgebrochen, Sir.")
                    return "Abgebrochen."

                step_num = step.get("step", "?")
                tool = step.get("tool", "generated_code")
                desc = step.get("description", "")
                params = step.get("parameters", {})

                logger.info(f"▶ Step {step_num}: [{tool}] {desc}")

                attempt = 1
                step_ok = False
                while attempt <= 3:
                    if cancel_flag and cancel_flag.is_set():
                        break
                    try:
                        result = self._call_tool(tool, params, speak)
                        logger.info(f"✅ Step {step_num} done: {str(result)[:100]}")
                        step_ok = True
                        break
                    except Exception as e:
                        logger.error(f"❌ Step {step_num} attempt {attempt} failed: {e}")
                        attempt += 1
                        time.sleep(1)

                if not step_ok:
                    failed_step = step
                    failed_error = str(e)
                    success = False
                    break

            if success:
                msg = f"Aufgabe abgeschlossen, Sir. {len(steps)} Schritte ausgeführt."
                if speak: speak(msg)
                return msg

            if replan_attempts >= self.MAX_REPLAN:
                msg = f"Aufgabe nach {replan_attempts} Versuchen fehlgeschlagen, Sir."
                if speak: speak(msg)
                return msg

            if speak: speak("Ich passe meinen Ansatz an, Sir.")
            replan_attempts += 1
            plan = replan(goal, [], failed_step, failed_error)

    def _call_tool(self, tool: str, params: dict, speak: Optional[Callable]) -> str:
        if tool == "open_app":
            from actions.open_app import open_app
            return open_app(parameters=params, player=None) or "Done."
        elif tool == "web_search":
            from actions.web_search import web_search
            return web_search(parameters=params, player=None) or "Done."
        elif tool == "file_controller":
            from actions.file_controller import file_controller
            return file_controller(parameters=params, player=None) or "Done."
        elif tool == "screen_process":
            from actions.screen_processor import screen_process
            return "Screen captured." if screen_process(parameters=params, player=None) else "Failed."
        elif tool == "computer_control":
            from actions.computer_control import computer_control
            return computer_control(parameters=params, player=None) or "Done."
        elif tool == "browser_control":
            from actions.browser_control import browser_control
            return browser_control(parameters=params, player=None) or "Done."
        elif tool == "computer_settings":
            from actions.computer_settings import computer_settings
            return computer_settings(parameters=params, player=None) or "Done."
        elif tool == "code_helper":
            from actions.code_helper import code_helper
            return code_helper(parameters=params, player=None) or "Done."
        elif tool == "send_message":
            from actions.send_message import send_message
            return send_message(parameters=params, player=None) or "Done."
        elif tool == "reminder":
            from actions.reminder import reminder
            return reminder(parameters=params, player=None) or "Done."
        else:
            return f"Unknown tool: {tool}"
