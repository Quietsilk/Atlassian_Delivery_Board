# Architecture

## Обзор

```
Browser (UI — read-only)
    │
    ├── GET  /latest?project=KEY       ← читает последний снапшот
    ├── GET  /history?project=KEY      ← читает историю
    └── POST /sync  { project, source, creds, jql }  ← запускает ингест в фоне
            │
            ▼
server.py  (тонкий HTTP-роутер, порт 5678)
            │
            ├── server/api.py          ← handle_get_latest, handle_get_history, handle_post_sync
            │
            ├── server/ingestion.py    ← _run_pipeline() — общий; run_ingestion (Jira) / run_ingestion_with_adapter
            │       │
            │       ├── fetch_jira()  — Jira-specific
            │       │       ├── POST /rest/api/3/search/jql  (пагинация, PAGE_SIZE=50)
            │       │       └── GET  /rest/api/3/issue/{key}/changelog  (параллельно, 10 потоков)
            │       │
            │       ├── server/adapters/  — Linear / Asana / ClickUp
            │       │       ├── base.py    Adapter ABC + build_adapter() + HTTP helpers
            │       │       ├── jira.py    JiraAdapter (канонический формат)
            │       │       ├── linear.py  LinearAdapter (GraphQL → canonical)
            │       │       ├── asana.py   AsanaAdapter (REST stories → canonical)
            │       │       └── clickup.py ClickUpAdapter (task history → canonical)
            │       │
            │       └── server/metrics.py
            │               ├── calculate_metrics(issues)   → structural KPIs
            │               └── calculate_flow_metrics(completed) → P50/P85 cycle time + TTM
            │
            ├── server/storage.py      ← SQLite CRUD
            │       └── snapshots(id, project_key, timestamp, metrics_json)
            │
            └── server/scheduler.py   ← daemon-поток, запускает run_ingestion по расписанию
                    └── SYNC_INTERVAL_SECONDS (default 3600)
```

---

## Архитектурные инварианты

**Инвариант 1 — UI read-only.**
Браузер никогда не инициирует расчёт метрик. Он только читает сохранённые снапшоты. Метрики считаются один раз при ingestion и сохраняются.

**Инвариант 2 — Иммутабельные снапшоты.**
Каждый запуск ingestion создаёт новую строку в SQLite. Никаких UPDATE/DELETE.

**Инвариант 3 — `completedCount` кумулятивный.**
Хранится нарастающим итогом. Throughput за период = `ΔcompletedCount`.

**Инвариант 4 — Пустой result не сохраняется.**
Если источник возвращает 0 задач, ingestion завершается ошибкой без INSERT.

**Инвариант 5 — Period без пересчёта.**
`GET /history` фильтрует строки SQLite по полю `timestamp`. Метрики не пересчитываются.

**Инвариант 6 — `calculate_metrics` без `period`.**
Функция `calculate_metrics(issues)` не принимает `cutoff`/`period`. Это чистая функция.

**Инвариант 7 — Адаптер-инвариант.**
Все адаптеры возвращают один canonical issue shape; `calculate_metrics()` не знает об источнике.

**Инвариант 8 — `wipItems` в каждом снапшоте.**
Список in-progress задач рассчитывается при ingestion и хранится вместе с метриками.

---

## SQLite-схема

```sql
CREATE TABLE snapshots (
    id           INTEGER PRIMARY KEY,
    project_key  TEXT NOT NULL,
    timestamp    TEXT NOT NULL,   -- ISO 8601
    metrics_json TEXT NOT NULL    -- JSON: cycleTimeP50, inProgressCount, reopenedCount, …
);
```

Данные только добавляются (INSERT). История хранится бессрочно.

---

## Пакет server/

| Модуль | Экспортирует | Назначение |
|---|---|---|
| `metrics.py` | `calculate_metrics(issues, mapped)`, `calculate_flow_metrics(completed)` | Чистые функции, нет side-эффектов |
| `storage.py` | `init_db`, `save_snapshot`, `get_latest`, `get_history` | SQLite CRUD |
| `ingestion.py` | `run_ingestion(…)`, `run_ingestion_with_adapter(…)` | fetch → `_run_pipeline` → save |
| `api.py` | `handle_get_latest`, `handle_get_history`, `handle_post_sync` | HTTP handlers |
| `scheduler.py` | `start_scheduler(projects, db_path, interval)` | Daemon-поток |
| `adapters/base.py` | `Adapter`, `build_adapter(source, config)` | ABC + фабрика + HTTP helpers |
| `adapters/{linear,asana,clickup}.py` | `*Adapter` | fetch + normalize → canonical |

---

## Слои данных

```
Source API (Jira / Linear / Asana / ClickUp)
            │
            ▼  Adapter.fetch_and_normalize()
    Canonical Issue (dict)
            fields: { created, resolutiondate, status: {name}, summary, assignee }
            changelog: { histories: [ { created, items: [ {field, fromString, toString} ] } ] }
            │
            ▼  _map_issue(issue)
    Mapped Issue (dict)
            started_at, resolved_at, created_at, reopened
            │
            ▼  calculate_metrics / calculate_flow_metrics
    Metrics dict
            cycleTimeP50, cycleTimeP85, timeToMarketP50, timeToMarketP85,
            flowEfficiencyPercent, inProgressCount, reopenedCount,
            backlogAgingDays, completedCount, throughput, wipItems
            │
            ▼  save_snapshot → SQLite
    Browser (UI)  KpiCard × 6 + AIPanel + StaleIssuesPanel
```

---

## Frontend (React 18 + Vite)

Запускается на порту 5173 (dev) или раздаётся через server.py (prod).

### Компоненты

| Компонент | Назначение |
|---|---|
| `App.jsx` | Root: layout, sync-flow с поллингом, multi-project tabs |
| `KpiCard.jsx` | KPI-карточка: status stripe, value, delta, insight, progress bar |
| `AIPanel.jsx` | Summary / Risks / Actions tabs; glowing dot при наличии analysis |
| `Sidebar.jsx` | Source picker, credentials form, status mapping, demo data |
| `StaleIssuesPanel.jsx` | WIP-задачи с aging/blocker индикаторами (коллапсируемая) |

### Хуки

| Хук | Назначение |
|---|---|
| `useTheme` | dark/light mode → `T` (токены), `toggleTheme` → localStorage (`ada:theme`) |
| `useCredentials` | Multi-source creds → localStorage (`ada:source`, `ada:creds-v2`) |
| `useProjects` | Multi-project tabs → localStorage (`ada:projects-v2`, `ada:activeId`) |

### LocalStorage-ключи

| Ключ | Содержимое |
|---|---|
| `ada:theme` | `"dark"` / `"light"` |
| `ada:source` | `"jira"` / `"linear"` / `"asana"` / `"clickup"` |
| `ada:creds-v2` | JSON: `{ jira:{baseUrl,email,apiToken}, linear:{apiKey,teamId}, … }` |
| `ada:projects-v2` | JSON: массив `{id, label, jql}` |
| `ada:activeId` | ID активного проекта |
| `ada:started-statuses` | Comma-separated статусы "In Progress" (status mapping) |
| `ada:done-statuses` | Comma-separated статусы "Done" (status mapping) |

### Sync flow

```
handleSync()  — синкает все проекты параллельно
    │
    Promise.all(projects.map → POST /sync)
    │
    poll каждые 3s: GET /history + GET /latest  (для активного проекта)
    │
    ├── новый snapshot timestamp → setSyncState("done")
    └── 20 попыток × 3s = 60s timeout → setSyncState("error")
```

---

## Статусная модель

```python
STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}
```

Все сравнения case-insensitive (`.lower()`). Пользователь может переопределить через Status Mapping в Sidebar (сохраняется в localStorage, передаётся в POST /sync).
