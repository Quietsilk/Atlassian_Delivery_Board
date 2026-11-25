# Atlassian Delivery Board

Локальный delivery-дашборд для Jira и Trello. Сервер синхронизирует настроенные профили, рассчитывает метрики по changelog/history и сохраняет иммутабельные SQLite-снапшоты. React-интерфейс читает готовые метрики и не получает credentials источников.

## Quick start

```bash
cp .env.example .env
chmod 600 .env
# Заполнить ADA_ACCESS_TOKEN, Jira/Trello credentials и ADA_PROFILES.

cd dashboard
npm ci
npm run build
cd ..
python3 server.py
```

Production UI: `http://127.0.0.1:5678/`.

Для frontend-разработки запустите backend и отдельно:

```bash
cd dashboard
npm run dev
# http://127.0.0.1:5173/
```

При первом открытии UI запрашивает `ADA_ACCESS_TOKEN`. После успешного входа сервер выдаёт HttpOnly session cookie. Jira/Trello credentials и конфигурация запросов остаются только на сервере.

## Configuration

Основные переменные:

| Variable | Purpose | Default |
|---|---|---|
| `ADA_ACCESS_TOKEN` | обязательный локальный секрет входа | required |
| `ADA_PROFILES` | JSON-массив серверных профилей | `[]` |
| `JIRA_BASE_URL` | Jira HTTPS origin | required for Jira |
| `JIRA_EMAIL` | Jira account email | required for Jira |
| `JIRA_API_TOKEN` | Jira API token | required for Jira |
| `TRELLO_API_KEY`, `TRELLO_TOKEN` | Trello server credentials | required for Trello |
| `DB_PATH` | SQLite path | `snapshots.db` |
| `SYNC_INTERVAL_SECONDS` | scheduler interval | `3600` |
| `ADA_SYNC_WORKERS` | sync workers | `2` |
| `ADA_SYNC_QUEUE_SIZE` | max queued/running profile jobs | `32` |
| `ADA_MAX_JIRA_ISSUES` | Jira issue cap | `2000` |
| `ADA_MAX_JIRA_PAGES` | Jira search page cap | `50` |
| `ADA_MAX_TRELLO_CARDS` | Trello card cap | `5000` |
| `ADA_INGESTION_DEADLINE_SECONDS` | cooperative run deadline | `300` |
| `ADA_ALLOWED_ORIGINS` | browser CORS allowlist | local `:5173`, `:5678` |
| `ADA_ALLOWED_JIRA_HOSTS` | exact self-hosted Jira hosts | none |

Jira profile example, kept on one line in `.env`:

```json
[{"id":"dev","label":"Development","source":"jira","project_key":"DEV","methodology":"scrum","jql":"project = DEV ORDER BY created DESC"}]
```

Trello profiles use `source: "trello"` and include `board_id`; credentials remain in `TRELLO_API_KEY` and `TRELLO_TOKEN`.

`.env` and `snapshots.db` are ignored. Keep `.env` mode `0600`; never commit, log, or paste its values.

## API

The frontend uses `/api` routes only:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/login` | access token -> HttpOnly session |
| `POST` | `/api/logout` | revoke current session |
| `GET` | `/api/session` | authenticated state |
| `GET` | `/api/profiles` | public profile metadata |
| `GET` | `/api/latest?project=KEY` | latest snapshot |
| `GET` | `/api/history?project=KEY` | snapshot history |
| `GET` | `/api/projects` | project keys in SQLite |
| `POST` | `/api/validate-profile` | validate configured Jira profile |
| `POST` | `/api/sync` | enqueue one or more profile IDs |
| `POST` | `/api/sync-all` | atomically enqueue selected/all profiles |
| `GET` | `/api/sync-status` | active and queued profile IDs |

Example sync body:

```json
{"profileId":"dev"}
```

The server accepts JSON objects only, requires `Content-Length`, limits bodies to 64 KiB, and enforces a read timeout. Browser requests never contain credentials, JQL, or board IDs.

## Sync model

Manual sync and scheduler share one bounded `SyncCoordinator`. Duplicate profile jobs are deduplicated. Sync All is one atomic queue operation: the entire batch is admitted or rejected with `429`.

Ingestion fails closed. Empty results, failed Jira changelogs, source caps, Trello action caps, request errors, or deadline expiry do not create a snapshot. A UI sync is complete only when the active project receives a new snapshot timestamp.

## Metrics

All metrics are calculated server-side from canonical Jira/Trello issues:

| Metric | Definition |
|---|---|
| Cycle Time | P50/P85 from latest start to Done |
| Time to Market | P50/P85 from creation to Done |
| Flow Efficiency | `cycleTimeP50 / timeToMarketP50 * 100`, capped at 100% |
| Sprint Completion | Scrum: completed tasks / final scope of latest closed sprint |
| Reopened Rate | Kanban: reopened / completed |
| WIP | current in-progress tasks |
| Backlog Aging | average age of backlog items |

Flow metrics use completed issues from the latest 30 days. If fewer than 10 exist, the fallback is the latest 10 completed issues, then all completed issues. Existing formulas and status mappings are product contracts and require explicit approval to change.

`StaleIssuesPanel` includes Task/Bug issues only, excludes Epics, and sorts oldest in-progress work first. Jira blocking is inferred from blocked-like statuses/labels; Trello uses workflow labels/list history.

## Project layout

```text
server.py                    local HTTP entry point
server/api.py                authenticated API handlers
server/security.py           sessions and JSON request reader
server/profiles.py           server-side profile validation
server/sync_coordinator.py   shared bounded queue
server/scheduler.py          periodic enqueue
server/ingestion.py          fetch, metrics, snapshot write
server/adapters/             Jira/Trello normalization
server/storage.py            SQLite snapshots
dashboard/src/               React 19 UI
tests/                       stdlib unittest regression suite
docs/architecture.md         detailed runtime contracts
SECURITY.md                  trust model and secret handling
```

Browser localStorage is limited to `ada:activeProjectId` and `ada:theme`. Legacy credential/project keys are removed at startup.

## Verification

```bash
python3 -m unittest discover -s tests

cd dashboard
npm ci
npm run lint
npm run build
npm audit --audit-level=high
npm audit --omit=dev --audit-level=high
```

CI also rejects tracked `.env`, database/key files, Atlassian token markers, and private-key headers.

## Security boundary

The server is intentionally loopback-only and single-user. Other OS users are untrusted; processes under the same OS account are trusted. This is not a public/LAN multi-user service. See [SECURITY.md](SECURITY.md) for the complete model.
