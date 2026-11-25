"""Bounded sync queue shared by HTTP requests and the scheduler."""

from collections import deque
import threading


class QueueFullError(Exception):
    pass


class SyncCoordinator:
    def __init__(self, db_path, *, worker_count=2, max_jobs=32, runner=None):
        if worker_count < 1 or max_jobs < worker_count:
            raise ValueError("invalid sync queue limits")
        self._db_path = db_path
        self._worker_count = worker_count
        self._max_jobs = max_jobs
        self._runner = runner
        self._queue = deque()
        self._active = set()
        self._condition = threading.Condition()
        self._started = False

    def start(self):
        with self._condition:
            if self._started:
                return
            self._started = True
            for index in range(self._worker_count):
                threading.Thread(
                    target=self._worker,
                    daemon=True,
                    name=f"sync-worker-{index + 1}",
                ).start()

    def enqueue(self, profiles):
        unique = []
        already_running = []
        with self._condition:
            for profile in profiles:
                profile_id = profile["id"]
                if profile_id in self._active:
                    already_running.append(profile_id)
                elif profile_id not in {item["id"] for item in unique}:
                    unique.append(profile)
            if len(self._active) + len(unique) > self._max_jobs:
                raise QueueFullError("sync queue is full")
            for profile in unique:
                self._active.add(profile["id"])
                self._queue.append(profile)
            if unique:
                self._condition.notify_all()
        return [profile["id"] for profile in unique], already_running

    def _worker(self):
        while True:
            with self._condition:
                while not self._queue:
                    self._condition.wait()
                profile = self._queue.popleft()
            try:
                runner = self._runner
                if runner is None:
                    from server.ingestion import run_ingestion_with_adapter
                    runner = run_ingestion_with_adapter
                runner(
                    profile["project_key"],
                    profile["source"],
                    profile["config"],
                    self._db_path,
                )
            except Exception as error:
                print(
                    f"[sync] error for {profile['id']} "
                    f"({profile['source']}): {type(error).__name__}"
                )
            finally:
                with self._condition:
                    self._active.discard(profile["id"])
                    self._condition.notify_all()

    def wait_idle(self, timeout):
        with self._condition:
            return self._condition.wait_for(lambda: not self._active, timeout=timeout)

    def status(self):
        with self._condition:
            queued = [profile["id"] for profile in self._queue]
            return {"active": sorted(self._active), "queued": queued}
