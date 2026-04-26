AI Delivery Analyst — UI Simplification & Consistency (Final v2)

Goal:
Make UI consistent with backend (interval-based), simple, and non-misleading.

Constraints:
- Do NOT change backend or API
- Work only in ai-delivery-analyst-dashboard.html
- Do NOT add new metrics or libraries

Core Rule:
All metrics = results since last update (NOT per period)

KPI (exactly 5, in order):
1. Throughput
2. Flow Efficiency (proxy)
3. Time to Market
4. Cycle Time
5. Reopened

Changes:

Throughput:
- Keep value as-is
- Sublabel: "tasks completed since last update"
- Do NOT show per-day or period

Flow Efficiency:
- Label: "Flow Efficiency (proxy)"
- Sublabel: "cycle time / total lead time"
- Add title tooltip explaining it's approximation

Cycle Time:
- Sublabel: "last active phase before completion"
- Tooltip: "Measured from last start to completion"

Time to Market:
- Sublabel: "created → completed"

Reopened:
- Sublabel: "issues reopened at least once"
- Tooltip: "Counts issues that moved from Done back to active state"

AI Block:
- Move directly below KPI row
- Add hints:
  - "Low throughput may indicate bottlenecks"
  - "Low flow efficiency may indicate waiting time"
  - "Reopened tasks may indicate quality issues"

Stale Data:
- Show "Updated X min ago"
- >30 min = warning, >120 min = critical

Empty State:
- Short title + 1-2 lines + max 4 bullets

Remove:
- Period picker
- Any /7d /30d
- Any period-based wording

Done when:
- UI matches interval logic
- No misleading labels
- Exactly 5 KPIs

---

Уточнения в процессе (26 апреля 2026):
- Графики избыточны и нормально не работают — удалены
- System Health панель удалена
- Итого 8 KPI-карточек вместо 5:
  - Строка 1: Throughput · Cycle Time · Time to Market · Flow Efficiency
  - Строка 2: Reopened · WIP · Backlog · Backlog Aging
- Throughput на фронте: completedCount дельта между последними 2 снапшотами
  (фикс always-zero при первом синке)
