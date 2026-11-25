# Architecture

## Runtime

AI Delivery Analyst is a local, single-process application:

```text
React 19 dashboard
    |
    | /api/* + HttpOnly session cookie
    v
server.py (loopback HTTP server)
    |-- server/api.py              request validation and authenticated handlers
    |-- server/security.py         login sessions and bounded JSON parser
    |-- server/profiles.py         validated server-side source profiles
    |-- server/sync_coordinator.py shared bounded queue
    |-- server/scheduler.py        periodic enqueue into the same queue
    |-- server/ingestion.py        Jira fetch, metrics, snapshot write
    |-- server/adapters/           Jira/Trello canonical adapters
    `-- server/storage.py          immutable SQLite snapshots
```

The dashboard never receives source credentials, JQL, or Trello board IDs. It receives public profile metadata and submits only `profileId`/`profileIds`.

## Authentication boundary

1. `POST /api/login` accepts `ADA_ACCESS_TOKEN` and creates an in-memory session.
2. The browser receives an `HttpOnly`, `SameSite=Strict` cookie; the token is not returned or persisted by the frontend.
3. All profile, snapshot, validation, and sync endpoints require the session.
4. Login attempts are rate-limited per client address.
5. `HOST` must be loopback; allowed browser origins are explicit.

Other OS users are untrusted. Processes running as the same OS user are inside the trust boundary. See `SECURITY.md`.

## API

| Method | Path | Contract |
|---|---|---|
| `POST` | `/api/login` | `{accessToken}` -> session cookie |
| `POST` | `/api/logout` | invalidate current session |
| `GET` | `/api/session` | authenticated state only |
| `GET` | `/api/profiles` | public profile metadata |
| `GET` | `/api/latest?project=KEY` | latest immutable snapshot |
| `GET` | `/api/history?project=KEY&period=30d` | snapshot history |
| `GET` | `/api/projects` | project keys present in SQLite |
| `POST` | `/api/validate-profile` | `{profileId}`; Jira `/myself` check |
| `POST` | `/api/sync` | `{profileId}` or `{profileIds}` |
| `POST` | `/api/sync-all` | one atomic batch, optional `{profileIds}` |
| `GET` | `/api/sync-status` | active and queued profile IDs |

JSON POST bodies must be `application/json` objects with a valid `Content-Length`. The parser enforces a 64 KiB limit and a five-second read timeout. Stable failures are `400`, `408`, `411`, `413`, and `415`.

Legacy unprefixed routes remain temporary aliases for local compatibility; frontend code uses `/api` only.

## Profiles and sync

`ADA_PROFILES` is a JSON array. A profile owns source, project key, methodology, query/board configuration, and a reference to server-side credentials. Credentials are shared environment values and are never accepted from the browser.

HTTP and scheduler calls use the same `SyncCoordinator`:

- queue size and workers are bounded;
- duplicate queued/running profile IDs are deduplicated;
- Sync All is admitted atomically, so a full batch is accepted or rejected;
- worker errors contain profile/source and exception type, not credentials;
- each successful ingestion writes one immutable snapshot.

## Fail-closed ingestion

Jira issue/page caps, Trello card caps, action/changelog caps, request failures, empty source results, and the global ingestion deadline abort the run before `save_snapshot`. Partial source data must never replace a valid snapshot.

The ingestion deadline is cooperative between bounded network calls; each outbound request also has its own timeout.

## Data and metrics

SQLite is the durable snapshot store. Rows are append-only. The frontend reads metrics; it does not calculate source truth. Metric definitions remain in `server/metrics.py` and must not change without explicit approval.

Jira and Trello normalize into one canonical issue shape before metric calculation. WIP details include only Task/Bug items; Epics are excluded. In-progress items are displayed oldest first.

## Frontend state

The browser persists only presentation state:

| Key | Value |
|---|---|
| `ada:activeProjectId` | active server profile ID |
| `ada:theme` | light/dark preference |

Legacy credential/project localStorage keys are removed on startup.
