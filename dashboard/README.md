# AI Delivery Analyst Dashboard

React/Vite dashboard for the `react-redesign` branch.

## Run

```bash
npm run dev
```

The dashboard runs on Vite and reads the backend at `http://localhost:5678`.

Sync is considered complete only when `/latest` returns a snapshot with a new `timestamp`. AI analysis is optional and does not block completion.

The sidebar is closed by default on page load.

## Data Contract

Backend snapshots are returned as:

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

`src/api.js` normalizes those backend fields for the React UI:

| Backend field | UI field |
|---|---|
| `cycleTimeP50` | `cycleTime` |
| `timeToMarketP50` | `timeToMarket` |
| `flowEfficiencyPercent` | `flowEfficiency` |
| `reopenedCount` | `reopened` |
| `inProgressCount` | `wip` |
| `backlogAgingDays` | `backlogAging` |

The UI displays 6 KPI cards: Cycle Time, Time to Market, Flow Efficiency, Reopened, WIP, Backlog Aging.

KPI values are based on the latest snapshot. History is used for deltas and sparklines.
