import os
import threading
import unittest
from unittest.mock import patch

from server.scheduler import _get_interval, _run_loop, start_scheduler


class FakeCoordinator:
    def __init__(self):
        self.calls = []

    def enqueue(self, profiles):
        self.calls.append(profiles)


class TestScheduler(unittest.TestCase):
    def test_default_interval(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_get_interval(), 3600)

    def test_configured_interval(self):
        with patch.dict(os.environ, {"SYNC_INTERVAL_SECONDS": "42"}):
            self.assertEqual(_get_interval(), 42)

    def test_invalid_interval_uses_default(self):
        with patch.dict(os.environ, {"SYNC_INTERVAL_SECONDS": "invalid"}):
            self.assertEqual(_get_interval(), 3600)

    def test_loop_enqueues_profiles_through_coordinator(self):
        profiles = [{"id": "a"}, {"id": "b"}]
        stop = threading.Event()
        coordinator = FakeCoordinator()
        original_enqueue = coordinator.enqueue
        def enqueue_once(items):
            original_enqueue(items)
            stop.set()
        coordinator.enqueue = enqueue_once
        thread = threading.Thread(target=_run_loop, args=(profiles, coordinator, 0, stop))
        thread.start()
        thread.join(timeout=1)
        self.assertEqual(coordinator.calls, [profiles])

    def test_start_scheduler_returns_daemon_thread(self):
        coordinator = FakeCoordinator()
        thread, stop = start_scheduler([], coordinator, interval=99999)
        self.assertTrue(thread.daemon)
        self.assertEqual(thread.name, "scheduler")
        stop.set()
        thread.join(timeout=1)


if __name__ == "__main__":
    unittest.main()
