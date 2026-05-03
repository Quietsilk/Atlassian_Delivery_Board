# AI Delivery Analyst

Система раннего обнаружения рисков доставки. Подключается к Jira, рассчитывает метрики из changelog, анализирует через OpenAI и отображает всё в браузерном дашборде — с фоновым синком и персистентным хранением снапшотов.

---

## Что делает

1. Забирает задачи из Jira по JQL (cursor-based пагинация)
2. Загружает changelog каждой задачи параллельно (10 потоков)
3. Рассчитывает delivery-метрики: Cycle Time, Time to Market, Flow Efficiency, Reopened, WIP, Backlog Aging
4. Сохраняет снапшот в SQLite (иммутабельно — только INSERT)
5. Анализирует метрики через OpenAI → Summary, Risks, Actions (опционально)
6. Дашборд читает снапшоты через REST API (read-only UI)
7. Фоновый планировщик автоматически синхронизирует проекты по расписанию

Если Jira-запрос возвращает 0 задач, ingestion не сохраняет новый снапшот. Это защищает дашборд от ложных all-zero данных при ошибочном JQL, credentials или пустой выборке.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/Quietsilk/AI-Delivery-Analyst
cd AI-Delivery-Analyst

# 2. Configure (AI и Telegram опциональны)
cp .env.example .env

# 3. Run
python3 server.py
# → http://localhost:5678
```

Jira credentials вводятся в дашборде и хранятся в localStorage браузера.

### Дашборд (React + Vite)

```bash
# Dev-режим
cd dashboard && npm install && npm run dev
# → http://localhost:5173  (требует запущенного server.py на :5678)

# Production build — раздаётся через server.py GET /
cd dashboard && npm run build
# → dashboard/dist/  →  http://localhost:5678
```

---

## Стек

- **Python 3.9+** — stdlib-only, zero dependencies
- **SQLite** — персистентное хранение снапшотов через `server/storage.py`
- **React 18 + Vite** — дашборд (`dashboard/`)
- **Jira Cloud REST API** — `/rest/api/3/search/jql` + `/rest/api/3/issue/{key}/changelog`
- **OpenAI Responses API** — модель `o4-mini`, опционально

---

## Структура проекта

```
ai-delivery-analyst/
├── server.py                          # Тонкий HTTP-роутер
├── server/
│   ├── __init__.py
│   ├── metrics.py                     # calculate_metrics(issues) — чистая функция
│   ├── storage.py                     # SQLite CRUD (init, save, get_latest, get_history)
│   ├── ingestion.py                   # fetch + metrics + save
│   ├── api.py                         # HTTP handlers (GET /latest, GET /history, POST /sync)
│   └── scheduler.py                   # Фоновый daemon-поток для автосинка
├── dashboard/                         # React 18 + Vite дашборд
│   ├── src/
│   │   ├── App.jsx                    # Корневой компонент: layout, sync, tweaks
│   │   ├── api.js                     # fetchLatest, fetchHistory, postSync
│   │   ├── demo.js                    # DEMO_HISTORY, DEMO_ANALYSIS
│   │   ├── components/
│   │   │   ├── KpiCard.jsx            # KPI-карточка: sparkline, delta, статус-бар
│   │   │   ├── AIPanel.jsx            # AI Insights: summary/risks/actions tabs
│   │   │   ├── Sidebar.jsx            # Jira creds, JQL, demo-кнопка
│   │   │   └── Sparkline.jsx          # SVG-спарклайн
│   │   └── hooks/
│   │       ├── useCredentials.js      # Jira creds → localStorage
│   │       └── useProjects.js         # Multi-project tabs → localStorage
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── test_metrics.py                # 44 теста
│   ├── test_storage.py                # 13 тестов
│   ├── test_ingestion.py              # 12 тестов
│   └── test_api.py                    # 8 тестов (77 итого)
├── docs/
│   ├── architecture.md
│   ├── backlog.md
│   └── risks.md
├── specs/                             # Версионированные ТЗ
├── .env.example
└── .env                               # Локальные секреты (не в git)
```

---

## API

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | React дашборд (`dashboard/dist/`) или redirect → `:5173` |
| `GET` | `/latest?project=KEY` | Последний снапшот проекта |
| `GET` | `/history?project=KEY` | История снапшотов |
| `POST` | `/sync` | Запустить ингест в фоне → `{ok, queued}` |

**GET /latest** — пример ответа:
```json
{
  "ok": true,
  "snapshot": {
    "timestamp": "2026-04-26T10:00:00+00:00",
    "metrics": {
      "cycleTimeP50": 5.0,
      "cycleTimeP85": 17.8,
      "timeToMarketP50": 12.0,
      "timeToMarketP85": 62.2,
      "flowEfficiencyPercent": 41.7,
      "completedCount": 147,
      "throughput": 3,
      "inProgressCount": 9,
      "reopenedCount": 2,
      "backlogSize": 56,
      "backlogAgingDays": 28.3,
      "predictabilityPercent": 59.1
    }
  }
}
```

**POST /sync** — пример запроса:
```json
{
  "project": "KEY",
  "baseUrl": "https://company.atlassian.net",
  "email": "you@company.com",
  "apiToken": "...",
  "jql": "project = KEY ORDER BY updated DESC"
}
```

`POST /sync` возвращает только `{ok, queued}`. UI считает синк успешным после появления нового snapshot `timestamp` в `/latest`; AI-анализ опционален и не является условием успешного синка.

---

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DB_PATH` | Путь к SQLite-файлу | `snapshots.db` |
| `SYNC_INTERVAL_SECONDS` | Интервал фонового синка | `3600` |
| `PROJECTS` | JSON-массив проектов для планировщика | `[]` |
| `OPENAI_API_KEY` | AI-анализ (опционально) | — |

**Пример PROJECTS:**
```json
[{"project":"KEY","baseUrl":"https://co.atlassian.net","email":"x@co.com","apiToken":"...","jql":"project=KEY"}]
```

---

## Метрики

Все метрики рассчитываются из Jira changelog — не из статических полей.

6 KPI-карточек в сетке 3×2:

| Метрика | Определение | Хорошо | Плохо |
|---|---|---|---|
| **Cycle Time** | P50/P85: последний старт → Done | P50 ≤ 5d | P50 ≥ 10d |
| **Time to Market** | P50/P85: создание → Done | P50 ≤ 10d | P50 ≥ 20d |
| **Flow Efficiency** | cycleTimeP50 / timeToMarketP50 × 100%, cap 100% | ≥ 40% | ≤ 15% |
| **Reopened** | Задачи, вернувшиеся из Done хотя бы раз | = 0 | ≥ 3 |
| **WIP** | Задачи в статусе In Progress | ≤ 5 | ≥ 15 |
| **Backlog Aging** | Среднее кол-во дней в бэклоге | ≤ 14d | ≥ 30d |

---

## Тесты

```bash
python3 -m unittest discover -s tests -v
```

77 тестов, zero external dependencies:

| Файл | Тестов | Покрытие |
|---|---|---|
| `test_metrics.py` | 44 | `calculate_metrics`, `calculate_flow_metrics`, `_percentile`, `_parse_dt` |
| `test_storage.py` | 13 | SQLite CRUD, иммутабельность, фильтрация по периоду |
| `test_ingestion.py` | 12 | completedCount, flow metrics interval |
| `test_api.py` | 8 | HTTP handlers, 400/404/202 статусы |

---

## Архитектурные инварианты

1. **UI read-only** — браузер только читает снапшоты, никогда не считает метрики
2. **Иммутабельные снапшоты** — только INSERT в SQLite, никогда UPDATE/DELETE
3. **`completedCount` = кумулятивный** — всего завершённых задач на момент синка
4. **Flow metrics раздельно** — `calculate_metrics` возвращает структурные метрики; `calculate_flow_metrics(completed_items)` — P50/P85 flow-метрики
5. **Пустой Jira-result не сохраняется** — если JQL вернул 0 задач, новый snapshot не создаётся
6. **`calculate_metrics` без period** — чистая функция, нет параметров cutoff/period

---

## Built with AI

Проект создан с использованием Claude (Anthropic) как основного инструмента разработки — итеративное написание ТЗ, генерация кода, обнаружение багов, написание тестов и QA.
