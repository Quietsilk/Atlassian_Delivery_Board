"""Security and contract tests for the authenticated HTTP API."""

import http.client
import http.server
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from server import api
from server.security import AuthManager
from server.storage import init_db, save_snapshot
from server.sync_coordinator import QueueFullError


METRICS = {"throughput": 5, "inProgressCount": 2, "backlogSize": 1}


class FakeCoordinator:
    def __init__(self):
        self.calls = []
        self.full = False

    def enqueue(self, profiles):
        if self.full:
            raise QueueFullError("sync queue is full")
        ids = [profile["id"] for profile in profiles]
        self.calls.append(ids)
        return ids, []

    def status(self):
        return {"active": [], "queued": []}


PROFILES = {
    "proj": {
        "id": "proj", "label": "Project", "project_key": "PROJ",
        "source": "jira", "methodology": "scrum",
        "issue_base_url": "https://company.atlassian.net",
        "config": {
            "base_url": "https://company.atlassian.net",
            "email": "user@example.com", "api_token": "test-token",
            "jql": "project=PROJ",
        },
    },
}


class ApiHandler(http.server.BaseHTTPRequestHandler):
    db_path = None
    auth = AuthManager("test-access-token")
    profiles = PROFILES
    coordinator = FakeCoordinator()

    def do_OPTIONS(self):
        api.handle_options(self)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        routes = {
            "/api/session": lambda: api.handle_get_session(self, self.auth),
            "/api/profiles": lambda: api.handle_get_profiles(self, self.profiles, self.auth),
            "/api/projects": lambda: api.handle_get_projects(self, self.db_path, self.auth),
            "/api/latest": lambda: api.handle_get_latest(self, self.db_path, self.auth),
            "/api/history": lambda: api.handle_get_history(self, self.db_path, self.auth),
            "/api/sync-status": lambda: api.handle_get_sync_status(self, self.coordinator, self.auth),
        }
        route = routes.get(path)
        if route:
            route()
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        routes = {
            "/api/login": lambda: api.handle_post_login(self, self.auth),
            "/api/logout": lambda: api.handle_post_logout(self, self.auth),
            "/api/sync": lambda: api.handle_post_sync(self, self.profiles, self.coordinator, self.auth),
            "/api/sync-all": lambda: api.handle_post_sync_all(self, self.profiles, self.coordinator, self.auth),
            "/api/validate-profile": lambda: api.handle_post_validate_profile(self, self.profiles, self.auth),
        }
        route = routes.get(self.path)
        if route:
            route()
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *_args):
        pass


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp.close()
        cls.db = temp.name
        init_db(cls.db)
        save_snapshot("PROJ", METRICS, cls.db)
        ApiHandler.db_path = cls.db
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), ApiHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        os.unlink(cls.db)

    def setUp(self):
        ApiHandler.auth = AuthManager("test-access-token")
        ApiHandler.coordinator = FakeCoordinator()
        self.cookie = self._login()

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def _request(self, path, *, body=None, cookie=True, content_type="application/json", origin=None):
        headers = {"Content-Type": content_type}
        if cookie and getattr(self, "cookie", None):
            headers["Cookie"] = self.cookie
        if origin:
            headers["Origin"] = origin
        data = json.dumps(body).encode() if isinstance(body, (dict, list)) else body
        return urllib.request.Request(
            self._url(path), data=data, headers=headers,
            method="POST" if body is not None else "GET",
        )

    def _login(self):
        req = self._request("/api/login", body={"accessToken": "test-access-token"}, cookie=False)
        with urllib.request.urlopen(req) as response:
            self.assertTrue(json.loads(response.read())["ok"])
            header = response.headers["Set-Cookie"]
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Strict", header)
        self.assertIn("Path=/", header)
        return header.split(";", 1)[0]

    def test_session_does_not_return_capability_token(self):
        with urllib.request.urlopen(self._request("/api/session")) as response:
            body = json.loads(response.read())
        self.assertTrue(body["authenticated"])
        self.assertNotIn("token", body)

    def test_invalid_login_is_rejected(self):
        req = self._request("/api/login", body={"accessToken": "wrong"}, cookie=False)
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req)
        self.assertEqual(error.exception.code, 403)

    def test_read_endpoint_requires_authentication(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self._request("/api/projects", cookie=False))
        self.assertEqual(error.exception.code, 401)

    def test_profiles_never_return_credentials_or_jql(self):
        with urllib.request.urlopen(self._request("/api/profiles")) as response:
            raw = response.read().decode()
            body = json.loads(raw)
        self.assertEqual(body["profiles"][0]["id"], "proj")
        for forbidden in ("api_token", "test-token", "email", "jql"):
            self.assertNotIn(forbidden, raw)

    def test_snapshot_endpoints_work_when_authenticated(self):
        with urllib.request.urlopen(self._request("/api/latest?project=PROJ")) as response:
            latest = json.loads(response.read())
        with urllib.request.urlopen(self._request("/api/history?project=PROJ")) as response:
            history = json.loads(response.read())
        self.assertEqual(latest["snapshot"]["metrics"]["throughput"], 5)
        self.assertEqual(len(history["snapshots"]), 1)

    def test_sync_accepts_profile_id_only(self):
        with urllib.request.urlopen(self._request("/api/sync", body={"profileId": "proj"})) as response:
            body = json.loads(response.read())
        self.assertEqual(body["queued"], ["proj"])
        self.assertEqual(ApiHandler.coordinator.calls, [["proj"]])

    def test_sync_rejects_unknown_profile(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self._request("/api/sync", body={"profileId": "unknown"}))
        self.assertEqual(error.exception.code, 404)

    def test_sync_all_is_one_atomic_enqueue(self):
        with urllib.request.urlopen(self._request("/api/sync-all", body={"profileIds": ["proj"]})) as response:
            body = json.loads(response.read())
        self.assertEqual(body["queued"], ["proj"])
        self.assertEqual(ApiHandler.coordinator.calls, [["proj"]])

    def test_sync_queue_full_returns_429(self):
        ApiHandler.coordinator.full = True
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self._request("/api/sync-all", body={"profileIds": ["proj"]}))
        self.assertEqual(error.exception.code, 429)

    def test_non_object_json_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self._request("/api/sync", body=["proj"]))
        self.assertEqual(error.exception.code, 400)

    def test_invalid_json_is_rejected(self):
        req = self._request("/api/sync", body=b"{", cookie=True)
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req)
        self.assertEqual(error.exception.code, 400)

    def test_wrong_content_type_is_rejected(self):
        req = self._request("/api/sync", body=b"{}", content_type="text/plain")
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req)
        self.assertEqual(error.exception.code, 415)

    def test_oversized_body_is_rejected_without_reading(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.putrequest("POST", "/api/sync")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Cookie", self.cookie)
        connection.putheader("Content-Length", str(64 * 1024 + 1))
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        connection.close()

    def test_missing_content_length_returns_411(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.putrequest("POST", "/api/sync")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Cookie", self.cookie)
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 411)
        connection.close()

    def test_disallowed_origin_is_rejected(self):
        req = self._request("/api/sync", body={"profileId": "proj"}, origin="https://evil.example")
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req)
        self.assertEqual(error.exception.code, 403)

    def test_jira_base_url_allowlist(self):
        self.assertEqual(
            api._validate_jira_base_url("https://company.atlassian.net/"),
            "https://company.atlassian.net",
        )
        for value in ("http://company.atlassian.net", "https://localhost", "https://evil.example"):
            with self.assertRaises(ValueError):
                api._validate_jira_base_url(value)

    def test_validate_profile_redacts_auth_errors(self):
        error = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
        with patch("server.api._validate_jira_credentials", side_effect=error):
            with urllib.request.urlopen(self._request("/api/validate-profile", body={"profileId": "proj"})) as response:
                body = json.loads(response.read())
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "Jira credentials are invalid")

    def test_validate_profile_does_not_return_account_metadata(self):
        account = {
            "accountId": "private-id",
            "displayName": "Private Name",
            "emailAddress": "private@example.com",
        }
        with patch("server.api._validate_jira_credentials", return_value=account):
            with urllib.request.urlopen(self._request(
                "/api/validate-profile", body={"profileId": "proj"}
            )) as response:
                body = json.loads(response.read())
        self.assertEqual(body, {"ok": True})


if __name__ == "__main__":
    unittest.main()
