"""Main-thread execution queue for safe bpy access."""

from __future__ import annotations

import queue
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

_JOB_QUEUE: queue.Queue = queue.Queue()
_TIMER_RUNNING = False
_TIMER_INTERVAL = 0.01

# Job states. A job moves queued -> running -> done, or queued -> cancelled/skipped.
QUEUED = "queued"
RUNNING = "running"
DONE = "done"
CANCELLED = "cancelled"
SKIPPED = "skipped"


class JobNotStartedError(TimeoutError):
    """The job timed out while still queued; it was cancelled and never ran."""


class JobStillRunningError(TimeoutError):
    """The job timed out after starting; Blender is still running it."""


class JobSkippedError(RuntimeError):
    """The job was dropped before running because its requester went away."""


@dataclass
class Job:
    func: Callable[[], Any]
    result_box: dict[str, Any]
    # Checked on the main thread right before running; False means skip the job.
    should_run: Callable[[], bool] | None = None
    state: str = QUEUED
    lock: threading.Lock = field(default_factory=threading.Lock)
    done: threading.Event = field(default_factory=threading.Event)


def _claim(job: Job) -> bool:
    """Move a queued job to running. False if it was cancelled or should be skipped."""
    with job.lock:
        if job.state != QUEUED:
            return False
        if job.should_run is not None:
            try:
                keep = job.should_run()
            except Exception:  # noqa: BLE001
                keep = False
            if not keep:
                job.state = SKIPPED
                job.done.set()
                return False
        job.state = RUNNING
        return True


def _run(job: Job) -> None:
    try:
        job.result_box["result"] = job.func()
        job.result_box["success"] = True
    except Exception as exc:  # noqa: BLE001
        job.result_box["success"] = False
        job.result_box["error"] = str(exc)
        job.result_box["traceback"] = traceback.format_exc()
    finally:
        with job.lock:
            job.state = DONE
        job.done.set()


def _timer() -> float | None:
    try:
        while True:
            job: Job = _JOB_QUEUE.get_nowait()
            try:
                if _claim(job):
                    _run(job)
            finally:
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


def submit(func: Callable[[], Any], should_run: Callable[[], bool] | None = None) -> Job:
    """Queue ``func`` for the main thread without waiting (the timer must be running)."""
    job = Job(func=func, result_box={}, should_run=should_run)
    _JOB_QUEUE.put(job)
    return job


def wait(job: Job, timeout: float) -> Any:
    """Wait for ``job``. On timeout, cancel it if it has not started yet."""
    if not job.done.wait(timeout):
        with job.lock:
            if job.state == QUEUED:
                job.state = CANCELLED
                job.done.set()
                raise JobNotStartedError(
                    f"Did not start within {timeout:g}s because Blender was busy; cancelled."
                )
        if job.state != DONE:
            raise JobStillRunningError(f"Still running in Blender after {timeout:g}s.")

    if job.state == SKIPPED:
        raise JobSkippedError("Skipped: the client that sent it disconnected.")
    if not job.result_box.get("success", False):
        raise RuntimeError(job.result_box.get("error") or "Unknown main-thread error")
    return job.result_box.get("result")


def run_on_main_thread(
    func: Callable[[], Any],
    timeout: float = 60.0,
    should_run: Callable[[], bool] | None = None,
) -> Any:
    """Schedule func on Blender's main thread and wait for the result.

    ``should_run`` is checked just before the job starts; returning False skips it
    (used to drop work whose client has already disconnected). A job that times out
    before starting is cancelled, so it never runs after nobody is waiting for it.
    """
    job = submit(func, should_run)
    ensure_timer()
    return wait(job, timeout)


def register() -> None:
    ensure_timer()


def unregister() -> None:
    stop_timer()
