"""Tests for server.adapters.base — retry logic, HTTP helpers, ABC, factory.

Coverage targets:
  normalize_status  — mapping, case-insensitivity, fall-through
  _with_retry       — success, 429/5xx retry, 4xx fast-fail, generic exc, backoff
  _http_get         — response parsed as JSON
  _http_post        — body serialised, Content-Type set, response parsed
  Adapter           — abstract methods raise, fetch_and_normalize composes
  build_adapter     — jira/linear dispatch, case/whitespace, unknown source
"""

import sys
import os
import json
import unittest
import urllib.error
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.adapters.base import (
    normalize_status,
    _with_retry,
    _http_get,
    _http_post,
    Adapter,
    build_adapter,
    CANONICAL_STARTED,
    CANONICAL_DONE,
)


# ── normalize_status ───────────────────────────────────────────────────────────

class TestNormalizeStatus(unittest.TestCase):

    def test_maps_known_lower_status(self):
        mapping = {"in progress": CANONICAL_STARTED, "done": CANONICAL_DONE}
        self.assertEqual(normalize_status("in progress", mapping), CANONICAL_STARTED)

    def test_case_insensitive_mapping(self):
        mapping = {"done": CANONICAL_DONE}
        self.assertEqual(normalize_status("DONE",   mapping), CANONICAL_DONE)
        self.assertEqual(normalize_status("Done",   mapping), CANONICAL_DONE)
        self.assertEqual(normalize_status("done",   mapping), CANONICAL_DONE)

    def test_strips_leading_trailing_whitespace(self):
        mapping = {"todo": "todo"}
        self.assertEqual(normalize_status("  Todo  ", mapping), "todo")

    def test_fall_through_returns_raw_name(self):
        self.assertEqual(normalize_status("CustomStatus", {}), "CustomStatus")

    def test_empty_string_falls_through(self):
        self.assertEqual(normalize_status("", {}), "")

    def test_empty_mapping(self):
        self.assertEqual(normalize_status("In Review", {}), "In Review")


# ── _with_retry ────────────────────────────────────────────────────────────────

class TestWithRetry(unittest.TestCase):

    def test_returns_value_on_first_success(self):
        result = _with_retry(lambda: 42)
        self.assertEqual(result, 42)

    def test_retries_on_429_rate_limit(self):
        attempts = [0]

        def fn():
            attempts[0] += 1
            if attempts[0] < 3:
                raise urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
            return "ok"

        with patch("time.sleep"):
            result = _with_retry(fn, max_attempts=3)
        self.assertEqual(result, "ok")
        self.assertEqual(attempts[0], 3)

    def test_retries_on_500_server_error(self):
        attempts = [0]

        def fn():
            attempts[0] += 1
            if attempts[0] < 2:
                raise urllib.error.HTTPError("url", 500, "Server Error", {}, None)
            return "recovered"

        with patch("time.sleep"):
            result = _with_retry(fn, max_attempts=3)
        self.assertEqual(result, "recovered")
        self.assertEqual(attempts[0], 2)

    def test_retries_on_503(self):
        attempts = [0]

        def fn():
            attempts[0] += 1
            if attempts[0] < 2:
                raise urllib.error.HTTPError("url", 503, "Unavailable", {}, None)
            return "up"

        with patch("time.sleep"):
            result = _with_retry(fn, max_attempts=3)
        self.assertEqual(result, "up")

    def test_fails_fast_on_401(self):
        def fn():
            raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            _with_retry(fn, max_attempts=3)
        self.assertEqual(ctx.exception.code, 401)

    def test_fails_fast_on_403(self):
        def fn():
            raise urllib.error.HTTPError("url", 403, "Forbidden", {}, None)

        with self.assertRaises(urllib.error.HTTPError):
            _with_retry(fn, max_attempts=3)

    def test_fails_fast_on_404(self):
        def fn():
            raise urllib.error.HTTPError("url", 404, "Not Found", {}, None)

        with self.assertRaises(urllib.error.HTTPError):
            _with_retry(fn, max_attempts=3)

    def test_raises_last_exc_when_max_attempts_exceeded(self):
        def fn():
            raise urllib.error.HTTPError("url", 500, "Error", {}, None)

        with patch("time.sleep"):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                _with_retry(fn, max_attempts=3)
        self.assertEqual(ctx.exception.code, 500)

    def test_retries_generic_exception(self):
        attempts = [0]

        def fn():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ConnectionError("timeout")
            return "ok"

        with patch("time.sleep"):
            result = _with_retry(fn, max_attempts=3)
        self.assertEqual(result, "ok")

    def test_exponential_backoff_sleeps(self):
        sleep_calls = []

        def fn():
            raise urllib.error.HTTPError("url", 500, "err", {}, None)

        with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            with self.assertRaises(urllib.error.HTTPError):
                _with_retry(fn, max_attempts=3, backoff=2.0)

        # 3 attempts → 3 sleeps: 2^0=1, 2^1=2, 2^2=4
        self.assertEqual(len(sleep_calls), 3)
        self.assertAlmostEqual(sleep_calls[0], 1.0)
        self.assertAlmostEqual(sleep_calls[1], 2.0)
        self.assertAlmostEqual(sleep_calls[2], 4.0)

    def test_single_attempt_no_retry(self):
        calls = [0]

        def fn():
            calls[0] += 1
            raise urllib.error.HTTPError("url", 500, "err", {}, None)

        with patch("time.sleep"):
            with self.assertRaises(urllib.error.HTTPError):
                _with_retry(fn, max_attempts=1)

        self.assertEqual(calls[0], 1)


# ── _http_get / _http_post ─────────────────────────────────────────────────────

class TestHttpHelpers(unittest.TestCase):

    def _ctx_manager(self, data: dict):
        """Return a mock response that works as context manager."""
        body = json.dumps(data).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_http_get_returns_parsed_json(self):
        with patch("urllib.request.urlopen", return_value=self._ctx_manager({"ok": True})):
            result = _http_get("http://example.com/api", {"Authorization": "Bearer tok"})
        self.assertEqual(result, {"ok": True})

    def test_http_get_sends_headers(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["headers"] = dict(req.headers)
            return self._ctx_manager({})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _http_get("http://example.com", {"X-Custom": "value"})

        self.assertIn("X-custom", captured["headers"])

    def test_http_post_returns_parsed_json(self):
        with patch("urllib.request.urlopen", return_value=self._ctx_manager({"created": True})):
            result = _http_post("http://example.com/api", {"Authorization": "Bearer tok"}, {"key": "value"})
        self.assertEqual(result, {"created": True})

    def test_http_post_serialises_body_as_json(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["data"] = req.data
            return self._ctx_manager({})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _http_post("http://example.com", {}, {"hello": "world"})

        self.assertEqual(json.loads(captured["data"]), {"hello": "world"})

    def test_http_post_sets_content_type_header(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["headers"] = dict(req.headers)
            return self._ctx_manager({})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _http_post("http://example.com", {}, {})

        self.assertIn("Content-type", captured["headers"])
        self.assertEqual(captured["headers"]["Content-type"], "application/json")

    def test_http_post_method_is_post(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured["method"] = req.get_method()
            return self._ctx_manager({})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _http_post("http://example.com", {}, {"x": 1})

        self.assertEqual(captured["method"], "POST")


# ── Adapter ABC ────────────────────────────────────────────────────────────────

class TestAdapterABC(unittest.TestCase):

    def test_fetch_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            Adapter().fetch()

    def test_normalize_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            Adapter().normalize([])

    def test_fetch_and_normalize_composes_fetch_and_normalize(self):
        class Concrete(Adapter):
            def fetch(self):
                return [{"raw": 1}]
            def normalize(self, raw):
                return [{"canonical": r["raw"]} for r in raw]

        result = Concrete().fetch_and_normalize()
        self.assertEqual(result, [{"canonical": 1}])

    def test_default_source_is_unknown(self):
        self.assertEqual(Adapter.source, "unknown")


# ── build_adapter ──────────────────────────────────────────────────────────────

class TestBuildAdapter(unittest.TestCase):

    def test_builds_jira_adapter(self):
        from server.adapters.jira import JiraAdapter
        adapter = build_adapter("jira", {
            "base_url": "https://j.test", "email": "u@t.com",
            "api_token": "tok", "jql": "project=X",
        })
        self.assertIsInstance(adapter, JiraAdapter)

    def test_builds_linear_adapter(self):
        from server.adapters.linear import LinearAdapter
        adapter = build_adapter("linear", {"api_key": "lin_key", "team_id": "team-1"})
        self.assertIsInstance(adapter, LinearAdapter)

    def test_linear_adapter_receives_filter(self):
        from server.adapters.linear import LinearAdapter
        adapter = build_adapter("linear", {
            "api_key": "k", "team_id": "t",
            "filter_": {"priority": {"eq": 1}},
        })
        self.assertIsInstance(adapter, LinearAdapter)
        self.assertEqual(adapter.filter_, {"priority": {"eq": 1}})

    def test_unknown_source_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            build_adapter("asana", {})
        self.assertIn("Supported: jira, linear", str(ctx.exception))

    def test_source_is_case_insensitive(self):
        from server.adapters.jira import JiraAdapter
        adapter = build_adapter("JIRA", {
            "base_url": "https://j.test", "email": "u@t.com",
            "api_token": "tok", "jql": "project=X",
        })
        self.assertIsInstance(adapter, JiraAdapter)

    def test_source_strips_whitespace(self):
        from server.adapters.linear import LinearAdapter
        adapter = build_adapter("  linear  ", {"api_key": "k", "team_id": "t"})
        self.assertIsInstance(adapter, LinearAdapter)

    def test_empty_source_defaults_to_jira(self):
        from server.adapters.jira import JiraAdapter
        adapter = build_adapter("", {
            "base_url": "https://j.test", "email": "u@t.com",
            "api_token": "tok", "jql": "project=X",
        })
        self.assertIsInstance(adapter, JiraAdapter)

    def test_none_source_defaults_to_jira(self):
        from server.adapters.jira import JiraAdapter
        adapter = build_adapter(None, {
            "base_url": "https://j.test", "email": "u@t.com",
            "api_token": "tok", "jql": "project=X",
        })
        self.assertIsInstance(adapter, JiraAdapter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
