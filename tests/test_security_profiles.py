import json
import threading
import unittest

from server.profiles import load_profiles, public_profile
from server.sync_coordinator import QueueFullError, SyncCoordinator


JIRA_CREDENTIALS = {
    "base_url": "https://company.atlassian.net",
    "email": "user@example.com",
    "api_token": "secret-token",
}


class TestProfiles(unittest.TestCase):
    def test_jira_profile_keeps_credentials_server_side(self):
        raw = json.dumps([{
            "id": "dev", "label": "Development", "source": "jira",
            "project_key": "DEV", "jql": "project=DEV", "methodology": "scrum",
        }])
        profile = load_profiles(raw, JIRA_CREDENTIALS)["dev"]
        public = public_profile(profile)
        self.assertEqual(public["project"], "DEV")
        self.assertNotIn("config", public)
        self.assertNotIn("jql", public)
        self.assertNotIn("api_token", public)

    def test_duplicate_profile_ids_are_rejected(self):
        item = {"id": "dev", "source": "jira", "project_key": "DEV", "jql": "project=DEV"}
        with self.assertRaises(ValueError):
            load_profiles(json.dumps([item, item]), JIRA_CREDENTIALS)

    def test_invalid_profile_source_is_rejected(self):
        raw = json.dumps([{"id": "x", "source": "unknown", "project_key": "X"}])
        with self.assertRaises(ValueError):
            load_profiles(raw, JIRA_CREDENTIALS)


class TestSyncCoordinator(unittest.TestCase):
    def test_batch_admission_is_atomic_when_queue_is_full(self):
        coordinator = SyncCoordinator(":memory:", worker_count=1, max_jobs=2, runner=lambda *_: None)
        profiles = [self._profile("a"), self._profile("b"), self._profile("c")]
        with self.assertRaises(QueueFullError):
            coordinator.enqueue(profiles)
        self.assertEqual(coordinator.status()["active"], [])

    def test_dedupe_covers_queued_and_running_jobs(self):
        release = threading.Event()
        coordinator = SyncCoordinator(":memory:", worker_count=1, max_jobs=4, runner=lambda *_: release.wait(1))
        coordinator.start()
        profile = self._profile("a")
        queued, already = coordinator.enqueue([profile])
        self.assertEqual(queued, ["a"])
        queued, already = coordinator.enqueue([profile])
        self.assertEqual(queued, [])
        self.assertEqual(already, ["a"])
        release.set()
        self.assertTrue(coordinator.wait_idle(1))

    def test_slot_is_released_after_runner_error(self):
        coordinator = SyncCoordinator(
            ":memory:", worker_count=1, max_jobs=2,
            runner=lambda *_: (_ for _ in ()).throw(RuntimeError("failure")),
        )
        coordinator.start()
        coordinator.enqueue([self._profile("a")])
        self.assertTrue(coordinator.wait_idle(1))
        self.assertEqual(coordinator.status()["active"], [])

    @staticmethod
    def _profile(profile_id):
        return {
            "id": profile_id, "project_key": profile_id.upper(),
            "source": "jira", "config": {},
        }


if __name__ == "__main__":
    unittest.main()
