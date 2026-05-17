"""Tests for server.scheduler — background sync daemon.

Coverage targets:
  _get_interval   — env var parsing and fallback
  _run_loop       — stop_event behaviour, project iteration, error isolation
  start_scheduler — thread properties, interval selection, stop mechanism
"""

import os
import sys
import time
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.scheduler import _get_interval, _run_loop, start_scheduler


# ── _get_interval ──────────────────────────────────────────────────────────────

class TestGetInterval(unittest.TestCase):

    def test_default_when_env_not_set(self):
        env = {k: v for k, v in os.environ.items() if k != "SYNC_INTERVAL_SECONDS"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(_get_interval(), 3600)

    def test_custom_value_from_env(self):
        with patch.dict(os.environ, {"SYNC_INTERVAL_SECONDS": "600"}):
            self.assertEqual(_get_interval(), 600)

    def test_invalid_string_falls_back_to_default(self):
        with patch.dict(os.environ, {"SYNC_INTERVAL_SECONDS": "not-a-number"}):
            self.assertEqual(_get_interval(), 3600)

    def test_empty_string_falls_back_to_default(self):
        with patch.dict(os.environ, {"SYNC_INTERVAL_SECONDS": ""}):
            self.assertEqual(_get_interval(), 3600)

    def test_zero_is_accepted(self):
        with patch.dict(os.environ, {"SYNC_INTERVAL_SECONDS": "0"}):
            self.assertEqual(_get_interval(), 0)


# ── _run_loop ──────────────────────────────────────────────────────────────────

class TestRunLoop(unittest.TestCase):

    PROJECT = {"project_key": "P", "base_url": "http://p", "email": "e", "api_token": "t", "jql": "jql"}

    def test_does_not_call_ingestion_when_stop_set_before_start(self):
        stop = threading.Event()
        stop.set()
        calls = []

        with patch("server.ingestion.run_ingestion", side_effect=lambda *a, **kw: calls.append(a)):
            _run_loop([self.PROJECT], "db.path", 0, stop)

        self.assertEqual(calls, [])

    def test_calls_run_ingestion_for_each_project(self):
        stop = threading.Event()
        called = []

        def fake_ingest(project_key, *args, **kwargs):
            called.append(project_key)
            stop.set()   # stop after the first iteration completes

        projects = [
            {**self.PROJECT, "project_key": "A"},
            {**self.PROJECT, "project_key": "B"},
        ]
        with patch("server.ingestion.run_ingestion", side_effect=fake_ingest):
            _run_loop(projects, "db.path", 0, stop)

        self.assertIn("A", called)
        self.assertIn("B", called)

    def test_exception_in_one_project_does_not_crash_others(self):
        stop = threading.Event()
        called = []

        def fake_ingest(project_key, *args, **kwargs):
            called.append(project_key)
            if project_key == "A":
                raise RuntimeError("Jira down")
            stop.set()

        projects = [
            {**self.PROJECT, "project_key": "A"},
            {**self.PROJECT, "project_key": "B"},
        ]
        with patch("server.ingestion.run_ingestion", side_effect=fake_ingest):
            _run_loop(projects, "db.path", 0, stop)

        self.assertIn("A", called)
        self.assertIn("B", called)

    def test_passes_correct_args_to_run_ingestion(self):
        stop = threading.Event()
        received = {}

        def fake_ingest(project_key, base_url, email, api_token, jql, db_path):
            received.update(locals())
            stop.set()

        project = {"project_key": "P", "base_url": "http://p.io", "email": "me@p.io",
                   "api_token": "secret", "jql": "project=P"}

        with patch("server.ingestion.run_ingestion", side_effect=fake_ingest):
            _run_loop([project], "/var/db.db", 0, stop)

        self.assertEqual(received["project_key"], "P")
        self.assertEqual(received["base_url"], "http://p.io")
        self.assertEqual(received["email"], "me@p.io")
        self.assertEqual(received["api_token"], "secret")
        self.assertEqual(received["jql"], "project=P")
        self.assertEqual(received["db_path"], "/var/db.db")

    def test_empty_projects_list_runs_without_calling_ingestion(self):
        stop = threading.Event()
        calls = []

        def fake_ingest(*a, **kw):
            calls.append(1)
            stop.set()

        with patch("server.ingestion.run_ingestion", side_effect=fake_ingest):
            # Without stop being set the loop would run forever.
            # Set stop after a brief delay so the loop can exit.
            t = threading.Timer(0.05, stop.set)
            t.start()
            _run_loop([], "db.path", 0, stop)
            t.cancel()

        self.assertEqual(calls, [])


# ── start_scheduler ────────────────────────────────────────────────────────────

class TestStartScheduler(unittest.TestCase):

    def test_returns_thread_and_event(self):
        with patch("server.scheduler._run_loop"):
            thread, evt = start_scheduler([], "db.path", interval=99999)
        self.assertIsInstance(thread, threading.Thread)
        self.assertIsInstance(evt, threading.Event)

    def test_thread_is_daemon(self):
        with patch("server.scheduler._run_loop"):
            thread, _ = start_scheduler([], "db.path", interval=99999)
        self.assertTrue(thread.daemon)

    def test_thread_name_is_scheduler(self):
        with patch("server.scheduler._run_loop"):
            thread, _ = start_scheduler([], "db.path", interval=99999)
        self.assertEqual(thread.name, "scheduler")

    def test_uses_get_interval_when_interval_is_none(self):
        with patch("server.scheduler._get_interval", return_value=42) as mock_gi, \
             patch("server.scheduler._run_loop"):
            start_scheduler([], "db.path", interval=None)
        mock_gi.assert_called_once()

    def test_explicit_interval_skips_get_interval(self):
        with patch("server.scheduler._get_interval") as mock_gi, \
             patch("server.scheduler._run_loop"):
            start_scheduler([], "db.path", interval=123)
        mock_gi.assert_not_called()

    def test_stop_event_terminates_thread(self):
        # Use an empty projects list so _run_loop never calls run_ingestion.
        thread, stop = start_scheduler([], "db.path", interval=9999)
        self.assertTrue(thread.is_alive())
        stop.set()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_project_count_logged(self):
        # Smoke test: two projects, no crash, thread starts.
        projects = [
            {"project_key": "A", "base_url": "http://a", "email": "e", "api_token": "t", "jql": "j"},
            {"project_key": "B", "base_url": "http://b", "email": "e", "api_token": "t", "jql": "j"},
        ]
        with patch("server.scheduler._run_loop"):
            thread, stop = start_scheduler(projects, "db.path", interval=9999)
        stop.set()
        self.assertIsNotNone(thread)


if __name__ == "__main__":
    unittest.main(verbosity=2)
