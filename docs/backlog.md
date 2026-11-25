# Бэклог

## В работе / ближайшее

- [ ] Конфигурация STARTED/DONE статусов через UI (сейчас — хардкод в `server/metrics.py`)
- [ ] `npm run build` → раздача `dashboard/dist/` через `server.py` (единый процесс)
- [ ] **autoSyncStale** — при загрузке проекта проверять timestamp последнего снапшота; если он старше часа, автоматически запускать `/sync`. Пока данные обновляются вручную или планировщиком.

## Метрики и аналитика

- [ ] Aging WIP — задачи в In Progress дольше заданного порога
- [x] Заблокированные задачи — определение по метке или статусу Jira/Trello
- [ ] Сравнение периодов (30d vs предыдущие 30d) на основе снапшотов
- [ ] Story points в метриках (velocity, scope completion)
- [x] Methodology KPI: Scrum показывает Sprint Completion, Kanban показывает Reopened Rate

## Инфраструктура

- [ ] Docker-образ для деплоя
- [ ] Админ-интерфейс для `ADA_PROFILES` (сейчас профили меняются только в `.env`; секреты в UI не допускаются)
- [ ] Экспорт истории снапшотов в CSV / PDF

## Интеграции

- [ ] Scrum: Jira Agile API для sprint predictability
- [ ] Slack webhook
- [ ] Confluence: публикация отчёта

## Готово ✅

- [x] **React+Vite дашборд** (май 2026): KpiCard, Sidebar, StaleIssuesPanel, useProjects, useTheme
- [x] Маппинг React API: `src/api.js` нормализует серверный `metrics_json` в поля интерфейса для `buildKpis()`
- [x] Переключение проектов в React-дашборде сбрасывает snapshots/analysis при смене activeId
- [x] Поток синхронизации: React завершает обновление только по новому timestamp; сервер не сохраняет пустой результат Jira
- [x] Полный редизайн UI/UX: шесть KPI-карточек 3×2 с дельтами, P85 и статус-барами
- [x] Demo-кнопка в сайдбаре — всегда видна, не зависит от состояния данных
- [x] Throughput — убран из дашборда (не рассчитывается без исторических данных)
- [x] Tab switch: переключение проекта автоматически загружает данные
- [x] Архитектурный рефакторинг (апрель 2026): `server/` пакет, SQLite, read-only UI, регрессионное покрытие
- [x] Persistent storage: SQLite снапшоты, иммутабельные строки, история бессрочно
- [x] Фоновый планировщик: daemon-поток, `ADA_PROFILES`, общая ограниченная очередь, `SYNC_INTERVAL_SECONDS`
- [x] Первичная загрузка и polling: `GET /api/latest` → 404 → `POST /api/sync` → опрос каждые 3 секунды
- [x] Интерфейс только читает `GET /latest` и `GET /history`
- [x] `POST /api/sync` и атомарный `/api/sync-all` → 202 queued (без метрик в ответе)
- [x] Учётные данные вынесены из браузера в серверные профили; старый localStorage очищается
- [x] Вход по access token и HttpOnly session cookie; endpoints данных и синхронизации требуют аутентификацию
- [x] Fail-closed лимиты и дедлайн загрузки Jira/Trello
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
