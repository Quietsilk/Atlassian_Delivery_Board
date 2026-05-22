"""Tests for server.api — HTTP endpoints (no metrics calls)."""

import sys
import os
import json
import sqlite3
import time
import unittest
import tempfile
import threading
import urllib.request
import urllib.error
import http.server
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.storage import init_db, save_snapshot
from server import api as api_module


def tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    init_db(f.name)
    return f.name


METRICS = {"cycleTimeDays": 3.0, "timeToMarketDays": 6.0, "throughput": 5,
           "flowEfficiencyPercent": 50.0, "backlogSize": 1, "inProgressCount": 2,
           "sprintCompletionPercent": 75.0}


class ApiHandler(http.server.BaseHTTPRequestHandler):
    """Minimal handler that wires server.api functions."""
    db_path = None
    jira_credentials = {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/latest":
            api_module.handle_get_latest(self, self.__class__.db_path)
        elif path == "/history":
            api_module.handle_get_history(self, self.__class__.db_path)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == "/sync":
            api_module.handle_post_sync(self, self.__class__.db_path, self.__class__.jira_credentials)
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *a): pass  # silence test output


class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = tmp_db()
        save_snapshot("PROJ", METRICS, cls.db)

        ApiHandler.db_path = cls.db
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), ApiHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        os.unlink(cls.db)

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def setUp(self):
        with api_module._SYNC_LOCK:
            api_module._SYNC_IN_PROGRESS.clear()

    def tearDown(self):
        with api_module._SYNC_LOCK:
            api_module._SYNC_IN_PROGRESS.clear()

    def _post_jira_sync(self, project="PROJ"):
        payload = json.dumps({
            "project": project, "baseUrl": "https://j.test",
            "email": "u@t.com", "apiToken": "tok", "jql": f"project={project}",
        }).encode()
        req = urllib.request.Request(
            self._url("/sync"), data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        return urllib.request.urlopen(req)

    def _wait_for_no_sync_in_progress(self, timeout=1):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with api_module._SYNC_LOCK:
                if not api_module._SYNC_IN_PROGRESS:
                    return True
            time.sleep(0.01)
        return False

    def test_get_latest_returns_snapshot(self):
        with urllib.request.urlopen(self._url("/latest?project=PROJ")) as r:
            body = json.loads(r.read())
        self.assertTrue(body["ok"])
        self.assertEqual(body["snapshot"]["metrics"]["throughput"], 5)

    def test_get_latest_404_for_unknown_project(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self._url("/latest?project=UNKNOWN"))
        self.assertEqual(ctx.exception.code, 404)

    def test_get_latest_400_without_project_param(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self._url("/latest"))
        self.assertEqual(ctx.exception.code, 400)

    def test_get_history_returns_list(self):
        with urllib.request.urlopen(self._url("/history?project=PROJ")) as r:
            body = json.loads(r.read())
        self.assertTrue(body["ok"])
        self.assertIsInstance(body["snapshots"], list)
        self.assertEqual(len(body["snapshots"]), 1)

    def test_get_history_with_period(self):
        with urllib.request.urlopen(self._url("/history?project=PROJ&period=30d")) as r:
            body = json.loads(r.read())
        self.assertTrue(body["ok"])
        # Recent snapshot must appear in 30d window
        self.assertEqual(len(body["snapshots"]), 1)

    def test_get_history_400_without_project(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self._url("/history"))
        self.assertEqual(ctx.exception.code, 400)

    def test_post_sync_returns_202_queued(self):
        with patch("server.ingestion.run_ingestion_with_adapter", return_value={}):
            with self._post_jira_sync() as r:
                body = json.loads(r.read())
                self.assertEqual(r.status, 202)
        self.assertTrue(body["ok"])
        self.assertTrue(body["queued"])

    def test_sync_does_not_return_metrics(self):
        with patch("server.ingestion.run_ingestion_with_adapter", return_value={}):
            with self._post_jira_sync() as r:
                body = json.loads(r.read())
        self.assertNotIn("metrics", body)
        self.assertNotIn("cycleTimeDays", body)

    def test_post_sync_dedupes_same_source_and_project_while_running(self):
        started = threading.Event()
        release = threading.Event()
        calls = []

        def fake_ingestion(project, source, config, db_path):
            calls.append((project, source))
            started.set()
            release.wait(timeout=2)

        with patch("server.ingestion.run_ingestion_with_adapter", side_effect=fake_ingestion):
            with self._post_jira_sync("PROJ") as r:
                first_body = json.loads(r.read())
                self.assertEqual(r.status, 202)
            self.assertTrue(started.wait(timeout=1))

            with self._post_jira_sync("PROJ") as r:
                second_body = json.loads(r.read())
                self.assertEqual(r.status, 202)

            release.set()
            self.assertTrue(self._wait_for_no_sync_in_progress())

        self.assertTrue(first_body["queued"])
        self.assertFalse(second_body["queued"])
        self.assertTrue(second_body["alreadyRunning"])
        self.assertEqual(calls, [("PROJ", "jira")])

    def test_post_sync_allows_new_run_after_previous_finishes(self):
        first_done = threading.Event()
        calls = []

        def fake_ingestion(project, source, config, db_path):
            calls.append((project, source))
            first_done.set()

        with patch("server.ingestion.run_ingestion_with_adapter", side_effect=fake_ingestion):
            with self._post_jira_sync("PROJ") as r:
                first_body = json.loads(r.read())
                self.assertEqual(r.status, 202)
            self.assertTrue(first_done.wait(timeout=1))
            self.assertTrue(self._wait_for_no_sync_in_progress())

            with self._post_jira_sync("PROJ") as r:
                second_body = json.loads(r.read())
                self.assertEqual(r.status, 202)
            self.assertTrue(self._wait_for_no_sync_in_progress())

        self.assertTrue(first_body["queued"])
        self.assertTrue(second_body["queued"])
        self.assertEqual(calls, [("PROJ", "jira"), ("PROJ", "jira")])

    def test_post_sync_rejects_unsupported_source(self):
        payload = json.dumps({
            "project": "PROJ",
            "source": "asana",
            "accessToken": "tok",
            "projectGid": "gid",
        }).encode()
        req = urllib.request.Request(
            self._url("/sync"), data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)
        body = json.loads(ctx.exception.read())
        self.assertIn("supported: jira, trello", body["error"])

    def test_post_sync_missing_project_returns_400(self):
        payload = json.dumps({"source": "jira"}).encode()
        req = urllib.request.Request(
            self._url("/sync"), data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)
        body = json.loads(ctx.exception.read())
        self.assertIn("project is required", body["error"])

    def test_post_sync_jira_missing_api_token_returns_400(self):
        payload = json.dumps({
            "project": "PROJ", "source": "jira",
            "baseUrl": "https://j.test", "email": "u@t.com",
            # apiToken intentionally omitted
            "jql": "project=PROJ",
        }).encode()
        req = urllib.request.Request(
            self._url("/sync"), data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)
        body = json.loads(ctx.exception.read())
        self.assertIn("jira requires", body["error"])

    def test_post_sync_jira_missing_jql_returns_400(self):
        payload = json.dumps({
            "project": "PROJ", "source": "jira",
            "baseUrl": "https://j.test", "email": "u@t.com", "apiToken": "tok",
            # jql intentionally omitted
        }).encode()
        req = urllib.request.Request(
            self._url("/sync"), data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    def _post_trello_sync(self, lookback_days):
        payload = {
            "project": "PROJ", "source": "trello",
            "apiKey": "key", "token": "tok", "boardId": "board",
        }
        if lookback_days != "__omit__":
            payload["lookbackDays"] = lookback_days
        req = urllib.request.Request(
            self._url("/sync"), data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        return urllib.request.urlopen(req)

    def test_post_sync_trello_invalid_lookback_string_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_trello_sync("abc")
        self.assertEqual(ctx.exception.code, 400)
        body = json.loads(ctx.exception.read())
        self.assertIn("lookbackDays", body["error"])

    def test_post_sync_trello_zero_lookback_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_trello_sync(0)
        self.assertEqual(ctx.exception.code, 400)

    def test_post_sync_trello_negative_lookback_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_trello_sync(-1)
        self.assertEqual(ctx.exception.code, 400)

    def test_post_sync_trello_too_large_lookback_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_trello_sync(366)
        self.assertEqual(ctx.exception.code, 400)

    def test_post_sync_trello_valid_custom_lookback_passed_to_adapter(self):
        captured = {}

        def fake_ingestion(project, source, config, db_path):
            captured.update(config)

        with patch("server.ingestion.run_ingestion_with_adapter", side_effect=fake_ingestion):
            with self._post_trello_sync(42) as r:
                body = json.loads(r.read())
                self.assertEqual(r.status, 202)
        self.assertTrue(body["ok"])
        self.assertEqual(captured["lookback_days"], 42)

if __name__ == "__main__":
    unittest.main(verbosity=2)
