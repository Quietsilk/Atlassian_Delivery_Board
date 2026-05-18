# Risks

## Активные

**STARTED/DONE статусы захардкожены.**
Если в Jira-проекте используются нестандартные названия статусов, `started_at` будет `None` у всех задач → Cycle Time и Time to Market = 0. Workaround: добавить статус в `STARTED`/`DONE` в `server/metrics.py` вручную. Долгосрочно — вынести в UI-конфиг.

**Legacy `/webhook/sync-report` блокирует HTTP-поток.**
`server_app.Handler._handle()` выполняется синхронно в обработчике запроса: fetch Jira (N×changelog) + OpenAI — может занять 30-60 сек на большом проекте. В это время сервер недоступен для других запросов. Workaround: использовать новый `POST /sync` (возвращает 202 сразу, выполняет ингест в фоне).

**SQLite не масштабируется горизонтально.**
Один writer, нет репликации. Достаточно для single-instance деплоя. При необходимости multi-instance — потребуется миграция на PostgreSQL.

**Один процесс, нет graceful shutdown.**
`server.py` не обрабатывает сигналы. При `Ctrl+C` в середине длинного Jira-запроса — запрос обрывается, снапшот не сохраняется. Некритично — следующий запуск начнёт с нуля.

## Снятые риски

~~Нет persistent storage~~ — реализовано: SQLite с иммутабельными снапшотами.
~~Нет scheduled/cron~~ — реализовано: `server/scheduler.py`, daemon-поток, `SYNC_INTERVAL_SECONDS`.
~~История теряется при очистке браузера~~ — история хранится в SQLite, localStorage больше не используется для истории.
~~TypeScript/Node.js версионные конфликты~~ — стек переведён на Python stdlib.
~~n8n как точка отказа~~ — n8n удалён, сервер самодостаточен.
~~Hard cut Telegram-сообщений~~ — реализован умный чанкинг.
~~Case-sensitive статусы (BUG-S01)~~ — исправлено, все сравнения через `.lower()`.
~~BUG-1: Done без resolutiondate~~ — changelog фетчится для всех задач.
~~BUG-2: Cycle Time от первого старта~~ — берётся последний STARTED перед done.
~~BUG-3: Reopened не фильтруется по периоду~~ — KPI заменена на methodology KPI: Sprint Completion для Scrum, Reopened Rate для Kanban.
~~BUG-4: Задачи In Progress → Backlog невидимы~~ — changelog для всех задач.
~~Jira API token истекал 30 апреля 2026~~ — риск снят, как future-risk больше не актуален.
~~BUG-5: Throughput дублировал completedCount в дашборде~~ — Throughput убран из KPI-сетки; `completedCount` остаётся кумулятивным полем для расчёта дельт.
