# Дашборд AI Delivery Analyst

Интерфейс на React 19 и Vite 8. Работает с локальным защищённым API и не хранит учётные данные Jira/Trello.

## Запуск

```bash
npm run dev
```

Vite запускается на `http://127.0.0.1:5173` и проксирует `/api` в сервер на `http://127.0.0.1:5678`.

Синхронизация считается завершённой только после появления нового `timestamp` в `/api/latest`. Получение ответа `202 queued` само по себе не означает обновление данных.

При первом открытии пользователь вводит `ADA_ACCESS_TOKEN`; сервер создаёт HttpOnly-сессию. После входа интерфейс загружает публичные серверные профили и отправляет на синхронизацию только их ID.

## Контракт данных

Сервер возвращает снапшоты в формате:

```json
{
  "timestamp": "2026-04-26T10:00:00+00:00",
  "metrics": {
    "cycleTimeP50": 5.0,
    "cycleTimeP85": 17.8,
    "timeToMarketP50": 12.0,
    "timeToMarketP85": 62.2,
    "flowEfficiencyPercent": 41.7,
    "reopenedCount": 2,
    "inProgressCount": 9,
    "backlogAgingDays": 28.3
  }
}
```

`src/api.js` нормализует поля сервера для React-интерфейса:

| Поле сервера | Поле интерфейса |
|---|---|
| `cycleTimeP50` | `cycleTime` |
| `timeToMarketP50` | `timeToMarket` |
| `flowEfficiencyPercent` | `flowEfficiency` |
| `reopenedCount` | `reopened` |
| `inProgressCount` | `wip` |
| `backlogAgingDays` | `backlogAging` |

Интерфейс показывает шесть KPI: Cycle Time, Time to Market, Flow Efficiency, методологический KPI, WIP и Backlog Aging.

Значения KPI берутся из последнего снапшота. История используется для дельт. В WIP-таблице отображаются только Task/Bug; Epic исключаются, старые задачи находятся сверху.

## Состояние браузера

В localStorage сохраняются только:

- `ada:activeProjectId` — активный профиль;
- `ada:theme` — тема оформления.

Старые ключи с учётными данными и конфигурацией проектов удаляются при запуске.
