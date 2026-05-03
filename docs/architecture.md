# Architecture

## Обзор

```
Browser (UI — read-only)
    │
    ├── GET  /latest?project=KEY       ← читает последний снапшот
    ├── GET  /history?project=KEY      ← читает историю
    └── POST /sync  { project, creds, jql }  ← запускает ингест в фоне
            │
            ▼
server.py  (тонкий HTTP-роутер, порт 5678)
            │
            ├── server/api.py          ← handle_get_latest, handle_get_history, handle_post_sync
            │
            ├── server/ingestion.py    ← fetch_jira → calculate_metrics → save_snapshot
            │       │
            │       ├── fetch_jira()
            │       │       ├── POST /rest/api/3/search/jql  (пагинация, PAGE_SIZE=50)
            │       │       └── GET  /rest/api/3/issue/{key}/changelog  (параллельно, 10 потоков)
            │       │
            │       └── server/metrics.py → calculate_metrics(issues)
            │               ├── Cycle Time        (последний started_at → resolved_at)
            │               ├── Time to Market    (created_at → resolved_at)
            │               ├── Flow Efficiency   (cycleTime / timeToMarket × 100, cap 100%)
            │               └── Backlog / WIP / Reopened
            │
            ├── server/storage.py      ← SQLite CRUD
            │       └── snapshots(id, project_key, timestamp, metrics_json)
            │
            └── server/scheduler.py   ← daemon-поток, запускает ingestion по расписанию
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

**Инвариант 4 — Пустой Jira-result не сохраняется.**
Если Jira-запрос возвращает 0 задач, ingestion завершается ошибкой без INSERT. Это предотвращает ложные all-zero снапшоты.

**Инвариант 5 — Period без пересчёта.**
`GET /history` фильтрует строки SQLite по полю `timestamp`. Метрики не пересчитываются.

**Инвариант 6 — `calculate_metrics` без `period`.**
Функция `calculate_metrics(issues)` не принимает `cutoff`/`period` в сигнатуре.

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
| `metrics.py` | `calculate_metrics(issues)` | Чистая функция, нет side-эффектов |
| `storage.py` | `init_db`, `save_snapshot`, `get_latest`, `get_history`, `get_previous_snapshot` | SQLite CRUD |
| `ingestion.py` | `run_ingestion(project_key, base_url, email, api_token, jql, db_path)` | Полный pipeline: fetch → metrics → save |
| `api.py` | `handle_get_latest`, `handle_get_history`, `handle_post_sync` | HTTP handlers |
| `scheduler.py` | `start_scheduler(projects, db_path, interval)` | Daemon-поток |

---

## Слои данных

```
Jira Raw Issue
    └── fields: status, created, resolutiondate
    └── changelog.histories[].items[field="status"]
            │
            ▼
    Mapped Issue (dict)
            started_at   ← последний переход в STARTED перед last_done
            resolved_at  ← resolutiondate или последний переход в DONE
            created_at   ← fields.created
            reopened     ← был ли переход DONE → не-DONE
            │
            ▼
    Metrics dict
            cycleTimeP50, cycleTimeP85, timeToMarketP50, timeToMarketP85,
            flowEfficiencyPercent, inProgressCount, reopenedCount,
            backlogAgingDays, completedCount, throughput
            │
            ▼
    SQLite snapshot
            project_key, timestamp, metrics_json
            │
            ▼  GET /latest или GET /history
    Browser (UI)
            KpiCard × 6 + AIPanel
```

---

## Frontend — два варианта

### main ветка: `ai-delivery-analyst-dashboard.html`

Однофайловый, без сборки, без фреймворков. Read-only UI.

**Ключевые функции:**

| Функция | Что делает |
|---|---|
| `refreshDashboard()` | GET /latest → updateDashboard + loadHistory; при 404 — auto-trigger POST /sync + polling |
| `loadHistory()` | GET /history → рисует SVG-спарклайны |
| `_postSync()` | POST /sync — запускает фоновый ингест |
| `_pollLatest(attempts)` | Поллинг GET /latest каждые 3s (до 20 попыток = ~60s) |
| `switchProject(id)` | Переключает таб → сбрасывает prevKpi → вызывает refreshDashboard |

### react-redesign ветка: `dashboard/` (React 19 + Vite)

Компонентный React-дашборд, запускается на порту 5173.

**Компоненты:**

| Компонент | Назначение |
|---|---|
| `App.jsx` | Root: layout, sync-flow с поллингом, tweaks-состояние |
| `KpiCard.jsx` | KPI-карточка: status stripe, большое значение, delta, P85, прогресс-бар |
| `AIPanel.jsx` | Summary / Risks / Actions tabs; glowing dot при наличии analysis |
| `Sidebar.jsx` | Jira credentials, JQL, `⚡ Load demo data` — всегда в сайдбаре |
| `Sparkline.jsx` | SVG polyline, цвет = зелёный если улучшение, серый иначе |
| `TweaksPanel` | Inline в App.jsx: kpiStyle (rich/minimal), density (comfortable/compact), aiTop |

**Хуки:**

| Хук | Назначение |
|---|---|
| `useCredentials` | Jira URL/email/token → localStorage (`ada:baseUrl`, `ada:email`, `ada:token`) |
| `useProjects` | Multi-project tabs → localStorage (`ada:projects-v2`) |

**LocalStorage-ключи (React-дашборд):**

| Ключ | Содержимое |
|---|---|
| `ada:baseUrl` | Jira URL |
| `ada:email` | Jira email |
| `ada:token` | Jira API token |
| `ada:projects-v2` | JSON: массив `{id, label, jql}` |

**Sync flow:**

```
handleSync()
    │
    POST /sync
    │
    poll каждые 3s: GET /history + GET /latest
    │
    ├── новый snapshot timestamp → setSyncState("done")
    └── 10 попыток × 3s = 30s timeout → setSyncState("error")
```

---

## Статусная модель Jira

```python
STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}
```

Все сравнения case-insensitive (`.lower()`). Changelog запрашивается для всех задач.
