# AI Delivery Analyst

Система раннего обнаружения рисков доставки. Подключается к Jira или Trello, рассчитывает метрики из changelog/history, анализирует через OpenAI и отображает всё в браузерном дашборде — с фоновым синком и персистентным хранением снапшотов.

---

## Что делает

1. Забирает задачи из выбранного источника (Jira / Trello) по проекту/борду
2. Загружает changelog/history каждой задачи параллельно
3. Рассчитывает delivery-метрики: Cycle Time, Time to Market, Flow Efficiency, Sprint Completion, WIP, Backlog Aging
4. Сохраняет снапшот в SQLite вместе со списком WIP-задач (`wipItems`) для детального разбора
5. Дашборд читает снапшоты через REST API (read-only UI)
6. Фоновый планировщик автоматически синхронизирует проекты по расписанию

Если запрос к источнику возвращает 0 задач, ingestion не сохраняет новый снапшот. Это защищает дашборд от ложных all-zero данных при ошибочном JQL, credentials или пустой выборке.

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

Credentials вводятся в дашборде и хранятся в localStorage браузера.

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
- **React 19 + Vite** — дашборд (`dashboard/`)
- **Jira Cloud REST API** — `/rest/api/3/search/jql` + changelog + Agile sprint report
- **Trello REST API** — cards + list movement actions

---

## Структура проекта

```
ai-delivery-analyst/
├── server.py                          # Тонкий HTTP-роутер
├── server/
│   ├── __init__.py
│   ├── metrics.py                     # calculate_metrics(issues) — чистая функция
│   ├── storage.py                     # SQLite CRUD (init, save, get_latest, get_history)
│   ├── ingestion.py                   # fetch + metrics + save; _compute_wip_items()
│   ├── api.py                         # HTTP handlers (GET /latest, GET /history, POST /sync)
│   ├── scheduler.py                   # Фоновый daemon-поток для автосинка
│   └── adapters/
│       ├── __init__.py                # build_adapter(), Adapter, CANONICAL_STARTED/DONE
│       ├── base.py                    # Базовый класс Adapter + фабрика
│       ├── jira.py                    # Jira REST → canonical issues
│       └── trello.py                  # Trello REST → canonical issues
├── dashboard/                         # React 19 + Vite дашборд
│   ├── src/
│   │   ├── App.jsx                    # Корневой компонент: layout, sync, staleness
│   │   ├── api.js                     # fetchLatest, fetchHistory, postSync (multi-source)
│   │   ├── demo.js                    # DEMO_HISTORY (с wipItems)
│   │   ├── tokens.js                  # Дизайн-токены (цвета, шрифты)
│   │   ├── components/
│   │   │   ├── KpiCard.jsx            # KPI-карточка: value, delta, insight, статус-бар
│   │   │   ├── Sidebar.jsx            # Source picker, credentials form
│   │   │   └── StaleIssuesPanel.jsx   # WIP-задачи с aging/blocker индикаторами
│   │   ├── context/
│   │   │   └── ThemeContext.js        # ThemeContext + useT()
│   │   └── hooks/
│   │       ├── useTheme.js            # dark/light mode → localStorage (ada:theme)
│   │       ├── useCredentials.js      # Multi-source creds → localStorage (ada:creds-v2)
│   │       └── useProjects.js         # Multi-project tabs → localStorage (ada:projects-v3)
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── test_metrics.py                # 44 теста
│   ├── test_storage.py                # 13 тестов
│   ├── test_ingestion.py              # 16 тестов
│   ├── test_ingestion_extended.py     # 34 теста
│   ├── test_api.py                    # 12 тестов
│   ├── test_adapters_base.py          # 33 теста
│   ├── test_adapters_trello.py        # 29 тестов
│   └── test_scheduler.py              # 17 тестов
├── docs/
│   ├── architecture.md
│   ├── backlog.md
│   └── risks.md
├── specs/                             # Версионированные ТЗ
├── .env.example
└── .env                               # Локальные секреты (не в git)
```

---

## Дизайн-система

### Токены (`dashboard/src/tokens.js`)

Единый источник цветов, типографики, отступов и анимаций. Все компоненты импортируют токены через `useT()` (тема-зависимые значения) или статические экспорты.

```js
import { getStatusColors, font, radius, transition } from "../tokens";
import { useT } from "../context/ThemeContext";
const T = useT();  // возвращает объект с токенами текущей темы
```

Поддерживаются два режима: **Dark (Calm)** и **Light**. Переключение через кнопку в шапке.

| Токен | Dark | Light | Назначение |
|---|---|---|---|
| `T.bg` | `#13151b` | `#f0f2f5` | Фон приложения |
| `T.brand` | `#6b8cff` | `#4f6fe8` | Акцент |
| `T.good` | `#4ade80` | `#16a34a` | Позитивный статус |
| `T.warn` | `#fbbf24` | `#b45309` | Предупреждение |
| `T.bad` | `#f87171` | `#dc2626` | Негативный статус |
| `T.bgCard` | `#1c1f28` | `#ffffff` | Фон карточки |

`getStatusColors(T, status)` возвращает `{ fg, bg, border, stripe }` для `good/warn/bad/neutral`.

### Формат дизайн-спеки (ТЗ)

| Формат | Когда |
|---|---|
| **JS-файл** (токены) | Новая палитра, обновление токенов — применяется напрямую |
| **Markdown** со структурой props / поведение / визуал | Новый компонент или фича |
| **Diff-описание** | Точечные изменения в существующем компоненте |

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
      "sprintCompletionPercent": 75.0,
      "sprintCommittedCount": 20,
      "sprintCompletedCount": 15,
      "sprintAddedCount": 4,
      "sprintRemovedCount": 2,
      "sprintCompletionBasis": "start_commitment",
      "sprintName": "Sprint 42",
      "backlogSize": 56,
      "backlogAgingDays": 28.3,
      "predictabilityPercent": 59.1,
      "wipItems": [
        {
          "key": "PROJ-118",
          "title": "Migrate auth service to OAuth 2.0",
          "assignee": "Alexey M.",
          "daysInProgress": 14,
          "status": "In Progress",
          "url": "https://company.atlassian.net/browse/PROJ-118",
          "blockedReason": "Waiting for security review"
        }
      ]
    }
  }
}
```

**POST /sync** — Jira:
```json
{
  "project": "KEY",
  "source": "jira",
  "baseUrl": "https://company.atlassian.net",
  "email": "you@company.com",
  "apiToken": "...",
  "jql": "project = KEY ORDER BY updated DESC"
}
```

**POST /sync** — Trello:
```json
{
  "project": "KEY",
  "source": "trello",
  "apiKey": "trello_api_key",
  "token": "trello_token",
  "boardId": "BOARD_ID"
}
```

`POST /sync` возвращает только `{ok, queued}`. UI считает синк успешным после появления нового snapshot `timestamp` в `/latest`.

---

## Источники данных

| Источник | Качество | Обязательные поля | Примечание |
|---|---|---|---|
| **Jira** | Высокое | `baseUrl`, `email`, `apiToken` | Полный changelog, JQL-фильтрация, Sprint Completion через Agile API |
| **Trello** | Высокое | `apiKey`, `token`, `boardId` | История через card actions, без Sprint Completion |

Все адаптеры нормализуют данные в единый канонический формат перед расчётом метрик — `calculate_metrics()` не знает об источнике.

---

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DB_PATH` | Путь к SQLite-файлу | `snapshots.db` |
| `SYNC_INTERVAL_SECONDS` | Интервал фонового синка | `3600` |
| `PROJECTS` | JSON-массив проектов для планировщика | `[]` |
| `OPENAI_API_KEY` | AI-анализ (опционально) | — |

**Пример PROJECTS (Jira):**
```json
[{"project":"KEY","source":"jira","baseUrl":"https://co.atlassian.net","email":"x@co.com","apiToken":"...","jql":"project=KEY"}]
```

---

## Метрики

Все метрики рассчитываются из changelog источника — не из статических полей.

6 KPI-карточек в сетке 3×2:

| Метрика | Определение | Хорошо | Плохо |
|---|---|---|---|
| **Cycle Time** | P50/P85: последний старт → Done | P50 ≤ 5d | P50 ≥ 10d |
| **Time to Market** | P50/P85: создание → Done | P50 ≤ 10d | P50 ≥ 20d |
| **Flow Efficiency** | cycleTimeP50 / timeToMarketP50 × 100%, cap 100% | ≥ 40% | ≤ 15% |
| **Sprint Completion** | completed committed tasks / tasks committed at sprint start × 100%, последний закрытый Jira-спринт. Если Jira report отдаёт пустой стартовый commitment, используется final scope без removed. | ≥ 85% | < 65% |
| **WIP** | Задачи в статусе In Progress | ≤ 5 | ≥ 15 |
| **Backlog Aging** | Среднее кол-во дней в бэклоге | ≤ 14d | ≥ 30d |

### WIP-детализация (StaleIssuesPanel)

Каждый снапшот содержит `wipItems` — список in-progress задач на момент синка. В дашборде отображается постоянно открытая панель с:

- возраст задачи (дней в In Progress): ≥14d красный, ≥7d жёлтый
- ссылка на задачу в источнике, если она доступна
- статус блокировки (`blockedReason`)
- исполнитель (аватар с инициалами)

---

## Индикаторы актуальности

**UpdatedAgo** — в шапке дашборда рядом с кнопкой Sync показывает, когда был последний синк: серый (≤30 мин), жёлтый (>30 мин), красный (>2 ч).

---

## Тесты

Тесты используют `pytest`:

```bash
python3 -m pytest
```

Zero external network dependencies:

| Файл | Тестов | Покрытие |
|---|---|---|
| `test_metrics.py` | 44 | `calculate_metrics`, `calculate_flow_metrics`, `_percentile`, `_parse_dt` |
| `test_storage.py` | 13 | SQLite CRUD, иммутабельность, фильтрация по периоду |
| `test_ingestion.py` | 16 | completedCount, flow metrics interval, sprintCompletion, wipItems |
| `test_ingestion_extended.py` | 34 | WIP details, adapter path, ingestion errors |
| `test_api.py` | 12 | HTTP handlers, 400/404/202 статусы, unsupported sources |
| `test_adapters_base.py` | 33 | Adapter ABC, retry/http helpers, Jira/Trello factory |
| `test_adapters_trello.py` | 29 | Trello adapter fetch/normalize |
| `test_scheduler.py` | 17 | Scheduler loop, project configs, intervals |

---

## Архитектурные инварианты

1. **UI read-only** — браузер только читает снапшоты, никогда не считает метрики
2. **Иммутабельные снапшоты** — только INSERT в SQLite, никогда UPDATE/DELETE
3. **`completedCount` = кумулятивный** — всего завершённых задач на момент синка
4. **Flow metrics раздельно** — `calculate_metrics` возвращает структурные метрики; `calculate_flow_metrics(completed_items)` — P50/P85 flow-метрики
5. **`calculate_metrics` без period** — чистая функция, нет параметров cutoff/period; источник не знает об адаптере
6. **Адаптер-инвариант** — все адаптеры возвращают один canonical issue shape; `calculate_metrics()` остаётся нетронутым при добавлении новых источников
7. **Пустой result не сохраняется** — если источник вернул 0 задач, новый snapshot не создаётся
8. **wipItems в каждом снапшоте** — список in-progress задач рассчитывается при ingestion и хранится вместе с метриками

---

## Built with AI

Проект создан с использованием Claude (Anthropic) как основного инструмента разработки — итеративное написание ТЗ, генерация кода, обнаружение багов, написание тестов и QA.
