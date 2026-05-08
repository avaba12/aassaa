"""Task-Queue für Hintergrund-Aufgaben."""
import threading, queue, time
from typing import Callable, Dict

class TaskQueue:
    def __init__(self):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="TaskQueue")
        self._thread.start()
        self._cancelled = set()

    def _worker(self):
        while True:
            try:
                task_id, func, args, kwargs = self._queue.get(timeout=1)
                if task_id in self._cancelled:
                    self._cancelled.discard(task_id)
                    continue
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    print(f"[TaskQueue] Error in task {task_id}: {e}")
            except queue.Empty:
                continue

    def submit(self, task_id: str, func: Callable, *args, **kwargs):
        self._queue.put((task_id, func, args, kwargs))

    def cancel(self, task_id: str):
        self._cancelled.add(task_id)
