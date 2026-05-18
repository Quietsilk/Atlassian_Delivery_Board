# Backlog

## В работе / ближайшее

- [ ] Конфигурация STARTED/DONE статусов через UI (сейчас — хардкод в `server/metrics.py`)
- [ ] `npm run build` → раздача `dashboard/dist/` через `server.py` (единый процесс)
- [ ] **autoSyncStale** — при загрузке проекта проверять timestamp последнего снапшота; если старше 1 часа — автоматически запускать `/sync`. Аналогично старому дашборду. Пока данные обновляются только вручную (кнопка Sync) или polling после синка.

## Метрики и аналитика

- [ ] Aging WIP — задачи в In Progress дольше threshold
- [ ] Blocked issues — детектирование по метке или статусу
- [ ] Сравнение периодов (30d vs предыдущие 30d) на основе снапшотов
- [ ] Story points в метриках (velocity, scope completion)
- [x] Methodology KPI: Scrum показывает Sprint Completion, Kanban показывает Reopened Rate

## Инфраструктура

- [ ] Docker-образ для деплоя
- [ ] Конфигурация PROJECTS через UI (сейчас только через env)
- [ ] Экспорт истории снапшотов в CSV / PDF

## Интеграции

- [ ] Scrum: Jira Agile API для sprint predictability
- [ ] Slack webhook
- [ ] Confluence: публикация отчёта

## Готово ✅

- [x] **React+Vite дашборд** (май 2026): `dashboard/` на ветке `react-redesign` — KpiCard, AIPanel, Sidebar, Sparkline, TweaksPanel, useCredentials, useProjects
- [x] React API mapping: `src/api.js` нормализует backend `metrics_json` в UI-поля для `buildKpis()`
- [x] Переключение проектов в React-дашборде сбрасывает snapshots/analysis при смене activeId
- [x] Sync flow: React завершает синк только по новому snapshot timestamp; backend не сохраняет пустой Jira-result
- [x] Full UI/UX redesign: 6 KPI-карточек 3×2 с sparklines, delta %, P85 и статус-барами
- [x] Demo-кнопка в сайдбаре — всегда видна, не зависит от состояния данных
- [x] Throughput — убран из дашборда (не рассчитывается без исторических данных)
- [x] Tab switch: переключение проекта автоматически загружает данные
- [x] Архитектурный рефакторинг (апрель 2026): `server/` пакет, SQLite, read-only UI, регрессионное покрытие
- [x] Persistent storage: SQLite снапшоты, иммутабельные строки, история бессрочно
- [x] Background scheduler: daemon-поток, `PROJECTS` env, `SYNC_INTERVAL_SECONDS`
- [x] Auto-sync + polling: GET /latest → 404 → POST /sync → poll 3s → auto-refresh
- [x] Read-only UI: браузер только читает GET /latest и GET /history
- [x] POST /sync → 202 queued (без метрик в ответе)
- [x] Flow Efficiency (5-я KPI, формула: cycleTime/timeToMarket×100, кап 100%)
- [x] Lead Time → Time to Market (rename везде: server, JSON, HTML, тесты)
- [x] UX overhaul: KPI-акценты, collapsible sidebar, empty state
- [x] Jira pagination (PAGE_SIZE=50, cursor-based)
- [x] Changelog fetch для всех задач
- [x] Case-insensitive статусная модель
- [x] Regression suite: pytest, zero external network dependencies
- [x] BUG-1: Done без resolutiondate корректно попадает в Throughput
- [x] BUG-2: Cycle Time от последнего старта перед done
- [x] BUG-3: Reopened KPI заменена на methodology KPI
- [x] BUG-4: Задачи In Progress → Backlog видимы (changelog для всех)
- [x] BUG-5: Throughput убран из KPI-сетки; `completedCount` оставлен как кумулятивное поле снапшота
