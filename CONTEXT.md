# AI Delivery Analyst - Project Context

Актуально на 25 ноября 2026 года.

## Repository

`https://github.com/Quietsilk/Atlassian_Delivery_Board`

Рабочая ветка: `dev`; изменения переходят в `main` только после review/approval.

## Stack

Python 3.9+ (stdlib), SQLite, Jira Cloud REST API, Trello REST API, React 19, Vite 8.

## Current architecture

- `server.py`: loopback-only HTTP router and static frontend server.
- `server/security.py`: access-token login, in-memory HttpOnly sessions, bounded JSON reader.
- `server/profiles.py`: validates `ADA_PROFILES`; keeps credentials/JQL/board configuration server-side.
- `server/sync_coordinator.py`: bounded queue shared by HTTP and scheduler.
- `server/ingestion.py`: source fetch, canonical mapping, metrics, immutable snapshot write.
- `server/storage.py`: SQLite CRUD.
- `dashboard/`: authenticated React dashboard; sends profile IDs only.

The browser never stores Jira/Trello credentials. It persists only `ada:activeProjectId` and `ada:theme`.

## Required configuration

```text
ADA_ACCESS_TOKEN=<random local secret>
JIRA_BASE_URL=https://company.atlassian.net
JIRA_EMAIL=<account email>
JIRA_API_TOKEN=<api token>
ADA_PROFILES=[{"id":"dev","label":"Development","source":"jira","project_key":"DEV","methodology":"scrum","jql":"project = DEV"}]
```

Keep `.env` ignored and mode `0600`. `HOST` must remain loopback. See `.env.example` and `SECURITY.md` for all limits and trust assumptions.

## API flow

1. `POST /api/login` exchanges `ADA_ACCESS_TOKEN` for an HttpOnly session cookie.
2. `GET /api/profiles` returns public profile metadata only.
3. `POST /api/sync` or `/api/sync-all` enqueues profile IDs.
4. Scheduler enqueues the same profiles through the same coordinator.
5. UI polls authenticated snapshot endpoints and treats a new timestamp as success.

## Invariants

1. Snapshot rows are append-only.
2. Metric formulas and source workflow mappings are preserved unless explicitly approved.
3. Empty or partial source data is never saved.
4. Jira/Trello caps and ingestion deadlines fail closed.
5. Sync All admission is atomic; duplicate profile jobs are deduplicated.
6. Task/Bug WIP is sorted oldest first; Epics are excluded.
7. Credentials never appear in browser storage, URLs, API responses, logs, docs, or Git.

## Verification

```bash
python3 -m unittest discover -s tests
cd dashboard
npm ci
npm run lint
npm run build
npm audit --audit-level=high
```

CI runs the same regression checks plus forbidden-file and secret-pattern guards.

## Known constraints

- STARTED/DONE mappings are static in `server/metrics.py`.
- SQLite and in-memory sessions are single-instance facilities.
- The service is local single-user software, not a LAN/Internet multi-user deployment.
- In-memory sessions and queued work are lost on process restart.
