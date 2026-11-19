"""Main-thread execution queue for safe bpy access."""

from __future__ import annotations

import queue
import traceback
from dataclasses import dataclass
from typing import Any, Callable

_JOB_QUEUE: queue.Queue = queue.Queue()
_TIMER_RUNNING = False
_TIMER_INTERVAL = 0.01


@dataclass
class Job:
    func: Callable[[], Any]
    result_box: dict[str, Any]


def _timer() -> float | None:
    global _TIMER_RUNNING
    try:
        while True:
            job: Job = _JOB_QUEUE.get_nowait()
            try:
                job.result_box["result"] = job.func()
                job.result_box["success"] = True
            except Exception as exc:  # noqa: BLE001
                job.result_box["success"] = False
                job.result_box["error"] = str(exc)
                job.result_box["traceback"] = traceback.format_exc()
            finally:
                job.result_box["done"] = True
                _JOB_QUEUE.task_done()
    except queue.Empty:
        pass

    if _JOB_QUEUE.empty() and not _TIMER_RUNNING:
        return None
    return _TIMER_INTERVAL


def ensure_timer() -> None:
    global _TIMER_RUNNING
    import bpy

    if not bpy.app.timers.is_registered(_timer):
        bpy.app.timers.register(_timer, first_interval=_TIMER_INTERVAL, persistent=True)
    _TIMER_RUNNING = True


def stop_timer() -> None:
    global _TIMER_RUNNING
    import bpy

    if bpy.app.timers.is_registered(_timer):
        bpy.app.timers.unregister(_timer)
    _TIMER_RUNNING = False


def run_on_main_thread(func: Callable[[], Any], timeout: float = 60.0) -> Any:
    """Schedule func on Blender's main thread and wait for the result."""
    import time

    result_box: dict[str, Any] = {"done": False}
    _JOB_QUEUE.put(Job(func=func, result_box=result_box))
    ensure_timer()

    start = time.time()
    while not result_box.get("done"):
        if time.time() - start > timeout:
            raise TimeoutError(f"Main-thread job timed out after {timeout}s")
        time.sleep(0.01)

    if not result_box.get("success", False):
        raise RuntimeError(result_box.get("error") or "Unknown main-thread error")
    return result_box.get("result")


def register() -> None:
    ensure_timer()


def unregister() -> None:
    stop_timer()
