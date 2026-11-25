# AI Delivery Analyst — контекст проекта

Актуально на 25 ноября 2026 года.

## Репозиторий

`https://github.com/Quietsilk/Atlassian_Delivery_Board`

Рабочая ветка: `dev`; изменения переходят в `main` только после ревью и одобрения.

## Стек

Python 3.9+ (стандартная библиотека), SQLite, Jira Cloud REST API, Trello REST API, React 19, Vite 8.

## Текущая архитектура

- `server.py`: локальный HTTP-роутер и сервер статического интерфейса.
- `server/security.py`: вход по access token, HttpOnly-сессии в памяти, ограниченный JSON reader.
- `server/profiles.py`: проверка `ADA_PROFILES`; учётные данные, JQL и параметры досок остаются на сервере.
- `server/sync_coordinator.py`: ограниченная очередь для HTTP и планировщика.
- `server/ingestion.py`: загрузка источника, нормализация, метрики, неизменяемый снапшот.
- `server/storage.py`: операции с SQLite.
- `dashboard/`: аутентифицированный React-дашборд; отправляет только ID профилей.

Браузер не хранит учётные данные Jira/Trello. Сохраняются только `ada:activeProjectId` и `ada:theme`.

## Обязательная конфигурация

```text
ADA_ACCESS_TOKEN=<random local secret>
JIRA_BASE_URL=https://company.atlassian.net
JIRA_EMAIL=<account email>
JIRA_API_TOKEN=<api token>
ADA_PROFILES=[{"id":"dev","label":"Development","source":"jira","project_key":"DEV","methodology":"scrum","jql":"project = DEV"}]
```

Файл `.env` должен игнорироваться Git и иметь права `0600`. `HOST` должен оставаться loopback-адресом. Все лимиты и допущения описаны в `.env.example` и `SECURITY.md`.

## Поток API

1. `POST /api/login` обменивает `ADA_ACCESS_TOKEN` на HttpOnly session cookie.
2. `GET /api/profiles` возвращает только публичные поля профилей.
3. `POST /api/sync` или `/api/sync-all` ставит ID профилей в очередь.
4. Планировщик использует ту же очередь и те же профили.
5. Интерфейс опрашивает защищённые endpoints и считает новый timestamp успешным обновлением.

## Архитектурные инварианты

1. Строки снапшотов только добавляются и не перезаписываются.
2. Формулы метрик и маппинг workflow не меняются без явного согласования.
3. Пустые или частичные данные источника не сохраняются.
4. Лимиты и дедлайны Jira/Trello работают по принципу fail-closed.
5. Sync All принимается атомарно; повторные задания одного профиля объединяются.
6. WIP содержит Task/Bug, сортируется от самых старых; Epic исключаются.
7. Учётные данные не попадают в браузерное хранилище, URL, API-ответы, логи, документацию и Git.

## Проверка

```bash
python3 -m unittest discover -s tests
cd dashboard
npm ci
npm run lint
npm run build
npm audit --audit-level=high
```

CI выполняет те же регрессионные проверки и дополнительно ищет запрещённые файлы и признаки секретов.

## Известные ограничения

- Маппинг STARTED/DONE статичен в `server/metrics.py`.
- SQLite и сессии в памяти рассчитаны на один экземпляр приложения.
- Сервис локальный и однопользовательский, а не многопользовательский LAN/Internet deployment.
- При перезапуске процесса сессии и задания в очереди теряются.
