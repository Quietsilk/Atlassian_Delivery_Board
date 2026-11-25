# Risks

## Активные

**STARTED/DONE статусы захардкожены.**
Если в Jira-проекте используются нестандартные названия статусов, `started_at` будет `None` у всех задач → Cycle Time и Time to Market = 0. Workaround: добавить статус в `STARTED`/`DONE` в `server/metrics.py` вручную. Долгосрочно — вынести в UI-конфиг.

**SQLite не масштабируется горизонтально.**
Один writer, нет репликации. Достаточно для single-instance деплоя. При необходимости multi-instance — потребуется миграция на PostgreSQL.

**Один процесс, нет graceful shutdown.**
`server.py` не обрабатывает сигналы. При `Ctrl+C` в середине длинного Jira-запроса — запрос обрывается, снапшот не сохраняется. Некритично — следующий запуск начнёт с нуля.

**Same-UID процессы находятся в доверенной зоне.**
Локальная auth-модель защищает от других OS users при корректных правах файлов, но не изолирует процессы, запущенные под тем же пользователем. Для более сильной границы нужен отдельный OS account или container.

**Старый SQLite blob остаётся в опубликованной Git-истории.**
Текущие файлы игнорируются и CI запрещает новые runtime DB/secrets, но удаление старого blob требует отдельного history rewrite, проверки всех canonical refs и force-push. Это намеренно не объединяется с обычным code change.

## Снятые риски

~~Нет persistent storage~~ — реализовано: SQLite с иммутабельными снапшотами.
~~Нет scheduled/cron~~ — реализовано: `server/scheduler.py`, daemon-поток, `SYNC_INTERVAL_SECONDS`.
~~История теряется при очистке браузера~~ — история хранится в SQLite, localStorage больше не используется для истории.
~~TypeScript/Node.js версионные конфликты~~ — стек переведён на Python stdlib.
~~n8n как точка отказа~~ — n8n удалён, сервер самодостаточен.
~~Legacy `/webhook/sync-report` блокировал HTTP-поток~~ — legacy `server_app.py` удалён; актуальный `POST /sync` возвращает 202 и выполняет ингест в фоне.
~~Session token был публично доступной anti-CSRF capability~~ — добавлен обязательный `ADA_ACCESS_TOKEN`, rate-limited login и in-memory HttpOnly session; все data/sync endpoints требуют auth.
~~Credentials и source config хранились в browser localStorage~~ — браузер получает только публичные profile metadata и отправляет profile IDs.
~~HTTP и scheduler запускали ingestion разными путями~~ — оба используют общую bounded queue; Sync All принимается атомарно.
~~Частичные Jira/Trello данные могли попасть в snapshot при достижении лимитов~~ — caps, changelog/action limits и deadline завершают ingestion без записи.
~~Jira credentials можно было отправить на произвольный `baseUrl`~~ — разрешены только HTTPS `*.atlassian.net` и точные hosts из `ADA_ALLOWED_JIRA_HOSTS`.
~~Trello credentials находились в query string~~ — credentials передаются через `Authorization` header и не выводятся в background error logs.
~~Hard cut Telegram-сообщений~~ — реализован умный чанкинг.
~~Case-sensitive статусы (BUG-S01)~~ — исправлено, все сравнения через `.lower()`.
~~BUG-1: Done без resolutiondate~~ — changelog фетчится для всех задач.
~~BUG-2: Cycle Time от первого старта~~ — берётся последний STARTED перед done.
~~BUG-3: Reopened не фильтруется по периоду~~ — KPI заменена на methodology KPI: Sprint Completion для Scrum, Reopened Rate для Kanban.
~~BUG-4: Задачи In Progress → Backlog невидимы~~ — changelog для всех задач.
~~Jira API token истекал 30 апреля 2026~~ — риск снят, как future-risk больше не актуален.
~~BUG-5: Throughput дублировал completedCount в дашборде~~ — Throughput убран из KPI-сетки; `completedCount` остаётся кумулятивным полем для расчёта дельт.
