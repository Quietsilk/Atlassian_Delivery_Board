# AI Delivery Analyst — Project Context

Стартовый контекст для AI-агента. Актуально на апрель 2026.

---

## Repository

https://github.com/Quietsilk/AI-Delivery-Analyst

## Стек

Python 3.9+ · stdlib only · SQLite · Jira Cloud REST API · OpenAI Responses API (o4-mini) · Vanilla JS/HTML дашборд

---

## Архитектура

Три слоя:

**`server.py`** — тонкий HTTP-роутер:
- `GET /` → отдаёт `ai-delivery-analyst-dashboard.html`
- `GET /latest?project=KEY` → последний снапшот из SQLite
- `GET /history?project=KEY&period=7d|30d|90d` → история снапшотов
- `POST /sync` → запускает `run_ingestion` в фоновом потоке → `{ok, queued}`

**`server/`** — пакет с бизнес-логикой:

| Модуль | Ключевые экспорты |
|---|---|
| `metrics.py` | `calculate_metrics(issues, mapped=None)` → структурные метрики; `calculate_flow_metrics(completed_items)` → P50/P85; `_map_issue`, `_percentile`, `_parse_dt` |
| `storage.py` | `init_db`, `save_snapshot`, `get_latest`, `get_history`, `get_previous_snapshot` |
| `ingestion.py` | `run_ingestion(...)`, `_get_completed_in_interval(mapped, since_ts)` |
| `api.py` | `handle_get_latest`, `handle_get_history`, `handle_post_sync` |
| `scheduler.py` | `start_scheduler(projects, db_path, interval)` |

**`ai-delivery-analyst-dashboard.html`** — read-only браузерный UI:
- Вводит Jira credentials (хранит в localStorage)
- Управляет проектными табами, автоматически переключает данные при смене таба
- При `GET /latest → 404` автоматически запускает `POST /sync` + поллит каждые 3s
- Параллельно запрашивает `GET /latest` и `GET /history`
- 6 KPI-карточек (3×2 сетка): Cycle Time · Time to Market · Flow Efficiency / Reopened · WIP · Backlog Aging
- AI-блок сразу под KPI; period picker и графики удалены (UI Simplification MVP)

---

## Архитектурные инварианты

1. **UI read-only** — браузер только читает снапшоты, никогда не считает метрики
2. **Иммутабельные снапшоты** — только INSERT в SQLite, никогда UPDATE/DELETE
3. **`throughput` (бэкенд) = интервальный** — кол-во resolved с `timestamp` предыдущего снапшота; 0 если нет предыдущего (не отображается в UI)
4. **`completedCount` = кумулятивный** — всего завершённых на момент синка; хранится в каждом снапшоте
5. **Flow metrics раздельно** — `calculate_metrics` → только `backlogSize, inProgressCount, completedCount, reopenedCount, backlogAgingDays`; `calculate_flow_metrics` → `cycleTimeP50/P85, timeToMarketP50/P85, flowEfficiencyPercent`
7. **Period фильтр удалён из UI** — `GET /history` без параметра; KPI всегда из последнего снапшота; агрегация по периоду не применяется
8. **`calculate_metrics` без period** — нет параметров cutoff/period в сигнатуре

---

## Статусы Jira

```python
STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}
```

Все сравнения case-insensitive. Changelog запрашивается для всех задач.

---

## Переменные окружения

| Переменная | Назначение | Дефолт |
|---|---|---|
| `DB_PATH` | Путь к SQLite-файлу | `snapshots.db` |
| `SYNC_INTERVAL_SECONDS` | Интервал фонового синка | `3600` |
| `PROJECTS` | JSON-массив проектов для планировщика | `[]` |
| `OPENAI_API_KEY` | AI-анализ (опционально) | — |
| `TELEGRAM_BOT_TOKEN` | Legacy Telegram (опционально) | — |
| `TELEGRAM_CHAT_ID` | Legacy Telegram (опционально) | — |

---

## Тесты

77 тестов в 4 файлах, stdlib unittest, zero deps:

```bash
python3 -m unittest discover -s tests -v
```

| Файл | Тестов |
|---|---|
| `tests/test_metrics.py` | 44 |
| `tests/test_storage.py` | 13 |
| `tests/test_ingestion.py` | 12 |
| `tests/test_api.py` | 8 |

---

## Известные ограничения

- STARTED/DONE статусы захардкожены в `server/metrics.py` (не конфигурируются через UI)
- Один JQL на проект (multi-source не реализован)
- SQLite не масштабируется горизонтально (single-writer)

---

## Хронология

1. TypeScript-прототип (src/) — выпилен в пользу Python (`6d88e48`)
2. Python stdlib HTTP-сервер + однофайловый HTML-дашборд
3. Jira API: POST /search/jql + changelog fetch
4. Пагинация (PAGE_SIZE=50, isLast loop)
5. Period-фильтр (7d/30d/90d/all)
6. localStorage-персистентность
7. Case-insensitive статусы (BUG-S01)
8. Smart Telegram chunking (BUG-S04)
9. Regression suite (33 → 61 → 87 тестов — legacy, удалён вместе с server_app.py)
10. UX overhaul: KPI-акценты, collapsible sidebar, period bar, AI/Risks иерархия
11. Flow Efficiency (5-я KPI), Time to Market rename, Throughput delta
12. **Архитектурный рефакторинг (апрель 2026):**
    - `server.py` → пакет `server/` (metrics, storage, ingestion, api, scheduler)
    - SQLite персистентное хранение снапшотов (иммутабельные строки)
    - Read-only UI: браузер только читает через GET /latest и GET /history
    - POST /sync → фоновый поток → 202 queued
    - Auto-sync + polling при 404 /latest
    - Throughput = дельта между снапшотами
    - Фоновый планировщик (PROJECTS env + SYNC_INTERVAL_SECONDS)
    - 108 тестов в 5 файлах
13. Tab switch: переключение проекта автоматически загружает его данные (`switchProject` async)
14. **Flow Metrics Refactor v2 (апрель 2026):**
    - P50/P85 перцентили вместо средних для Cycle Time и Time to Market
    - `calculate_metrics` разделён: структурные → `calculate_metrics`, flow → `calculate_flow_metrics`
    - Интервальная фильтрация: flow metrics считаются только по задачам, завершённым с последнего снапшота
    - `completedCount` — новое кумулятивное поле; `throughputPerDay` вычисляется фронтом
    - Статус: одна метка "Updated Xm ago" вместо чипов Connected/Refreshed
    - `wipRatio` удалён
    - Period-фильтр обновляет KPI-карточки (раньше только графики)
    - 120 тестов
15. **UI Simplification MVP (апрель 2026):**
    - Period picker удалён — метрики всегда interval-based (последний снапшот)
    - Графики удалены (chart panels, drawChart, drawThroughputChart, loadHistory)
    - AI-блок поднят сразу под KPI; статические hints при отсутствии OpenAI
    - Stale data: >30 мин — amber, >120 мин — red
    - Empty state: короткий заголовок + 4 буллета
    - Auto-sync при открытии страницы если данные старше 1 часа
16. **KPI Refinement (апрель 2026):**
    - 6 KPI-карточек в сетке 3×2: Cycle Time · Time to Market · Flow Efficiency · Reopened · WIP · Backlog Aging
    - Throughput и Backlog удалены из UI (данные остаются в снапшотах)
