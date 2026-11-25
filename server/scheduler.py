"""Background scheduler — runs ingestion on a fixed interval.

Interval is taken from ENV: SYNC_INTERVAL_SECONDS (default: 3600).
Start with: start_scheduler(projects, db_path) — runs in a daemon thread.
"""

import os
import time
import threading


_DEFAULT_INTERVAL = 3600  # 1 hour


def _get_interval():
    try:
        return int(os.environ.get("SYNC_INTERVAL_SECONDS", _DEFAULT_INTERVAL))
    except (ValueError, TypeError):
        return _DEFAULT_INTERVAL


def _run_loop(profiles, coordinator, interval, stop_event):
    """Core loop: sleep, then enqueue every configured profile."""
    while not stop_event.is_set():
        stop_event.wait(interval)
        if stop_event.is_set():
            break
        try:
            coordinator.enqueue(profiles)
        except Exception as error:
            print(f"[scheduler] enqueue error: {type(error).__name__}")


def start_scheduler(profiles, coordinator, interval=None):
    """Start background ingestion loop. Returns (thread, stop_event).

    profiles: validated server-side profiles
    """
    if interval is None:
        interval = _get_interval()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_run_loop,
        args=(profiles, coordinator, interval, stop_event),
        daemon=True,
        name="scheduler",
    )
    thread.start()
    print(f"[scheduler] started — interval {interval}s, {len(profiles)} profile(s)")
    return thread, stop_event
