# Design System — Atlassian Delivery Board

Единственный источник правды для цветов, типографики, отступов и анимаций.  
Файл: `src/tokens.js`

Поддерживаются две темы: **Light** и **Dark**. Light — основная тема в Atlassian-inspired стиле.

---

## Использование

```js
import { getStatusColors, font, radius, transition } from "../tokens";
import { useT } from "../context/ThemeContext";

const T = useT();  // тема-зависимые токены: цвета, тени
const sc = getStatusColors(T, "warn");  // { fg, bg, border, stripe }
```

---

## Цвета (тема-зависимые через `T`)

### Canvas

| Токен | Dark | Light | Назначение |
|---|---|---|---|
| `T.bg` | `#0C111B` | `#F4F5F7` | root background |
| `T.bgBar` | `#101828` | `#FFFFFF` | app bar |
| `T.bgCard` | `#182230` | `#FFFFFF` | KPI-карточки, панели |
| `T.bgSidebar` | `#111827` | `#FAFBFC` | сайдбар |

### Brand

| Токен | Dark | Light | Назначение |
|---|---|---|---|
| `T.brand` | `#579DFF` | `#0052CC` | акцент: primary actions, активные табы |
| `T.brandBg` | `rgba(87,157,255,0.14)` | `#DEEBFF` | фон brand-элементов |
| `T.brandBdr` | `rgba(87,157,255,0.38)` | `#B3D4FF` | рамка brand-элементов |
| `T.brandFocus` | `#85B8FF` | `#4C9AFF` | border при :focus |
| `T.brandGlow` | `rgba(87,157,255,0.10)` | `#F4F8FF` | bg при :focus |

### Статусы

| Токен | Dark | Light | Назначение |
|---|---|---|---|
| `T.good` / `T.goodBg` / `T.goodBdr` | `#57D9A3` | `#00875A` | позитивный |
| `T.warn` / `T.warnBg` / `T.warnBdr` | `#F5CD47` | `#974F0C` | предупреждение |
| `T.bad` / `T.badBg` / `T.badBdr` | `#F87168` | `#DE350B` | критический |
| `T.demo` / `T.demoBg` / `T.demoBdr` | `#9F8FEF` | `#6554C0` | demo-данные |

**Правило:** `getStatusColors(T, status)` → `{ fg, bg, border, stripe }` — не писать switch/if.

### Текст

| Токен | Dark | Light | Назначение |
|---|---|---|---|
| `T.text` | `#F9FAFB` | `#172B4D` | основной текст, KPI-значения |
| `T.textSec` | `#D0D5DD` | `#42526E` | вторичный текст |
| `T.textMuted` | `#98A2B3` | `#6B778C` | field labels |
| `T.textFaint` | `#667085` | `#8993A4` | section labels |
| `T.textLabel` | `#B3B9C4` | `#42526E` | заголовки KPI-карточек |

---

## Типографика (`font`)

Базовый размер `rem` в приложении: `20px`.

### Размеры (font.size)

| Токен | rem | Применение |
|---|---|---|
| `xxs` | 0.62rem | section labels |
| `xs` | 0.67rem | field labels, sublabels KPI |
| `sm` | 0.72rem | mono-значения, secondary текст |
| `base` | 0.78rem | инпуты, основной текст |
| `md` | 0.82rem | secondary text |
| `lg` | 0.88rem | логотип |
| `kpiSm` | 1.7rem | значение KPI в compact-режиме |
| `kpiLg` | 2.1rem | значение KPI в comfortable-режиме |

### Семейства

- **Sans**: `Inter, system-ui` — весь UI
- **Mono**: `IBM Plex Mono` — JQL, P85, timestamps

### Веса (`font.weight`)

`400 regular` / `500 medium` / `600 semibold` / `700 bold` / `800 extrabold`

---

## Радиусы (`radius`)

| Токен | px | Применение |
|---|---|---|
| `radius.sm` | 3 | маленькие кнопки, lozenge |
| `radius.md` | 4 | status pill, connect button |
| `radius.input` | 3 | все инпуты |
| `radius.card` | 4 | KPI-карточки |
| `radius.panel` | 4 | AIPanel |

---

## Анимации (`transition`)

| Токен | Значение | Применение |
|---|---|---|
| `transition.fast` | `0.15s ease` | hover-эффекты, opacity |
| `transition.normal` | `0.20s ease` | смена темы, раскрытие панелей |
| `transition.sidebar` | `width 0.22s cubic-bezier(0.4,0,0.2,1)` | sidebar toggle |
| `transition.kpiBar` | `width 0.60s ease` | progress bar в KpiCard |

---

## Компоненты

### KpiCard

```
┌─────────────────────────────────────────┐
│ Label                         GOOD      │
│ sublabel                                │
│                                         │
│ 4.2 d          -1.9d vs last            │
│ 1 item >14d in progress ← insight       │
│ ████████░░░░  (progress bar)           │
└─────────────────────────────────────────┘
```

Status отображается lozenge-бейджем справа в заголовке карточки. Верхний status stripe не используется.

### StaleIssuesPanel

StaleIssuesPanel отображается как плоский Jira backlog-like issue list без внешней рамки панели. Над таблицей отображаются quick filters: `All`, `Aging`, `Blocked`, `Unassigned`; строки группируются по текущему статусу.

```text
All 5   Aging 3   Blocked 2   Unassigned 0

IN PROGRESS 3
Key      Summary                    Status       Assignee     Age
PROJ-1   Payment retry handling      IN PROGRESS  Alexey M.    14d
```

Key отображается как ссылка, если доступен URL задачи. Age отображается lozenge-бейджем справа.

**Delta** — формат зависит от типа метрики:
- Flow (Cycle Time, TTM): `±Xd vs last` — скрывается если throughput < 5 или нет prev
- Snapshot (WIP, Backlog): `+3 (−44%)` — абсолютное + относительное %
- Проценты (Flow Efficiency, Sprint Completion, Reopened Rate): `±X% vs last`

**Insight** — детерминированный текст, рассчитывается в `buildInsight()` в App.jsx на основе `metrics + wipItems`. Цвет: `T.bad` / `T.warn` / `T.textMuted`.

`getStatusColors(T, status)` → `{ fg, bg, border, stripe }`.

### StatusPill (app bar)

| State | Color | Label |
|---|---|---|
| `idle` | `T.textMuted` | Idle |
| `syncing` | `T.warn` | Syncing… + spinner |
| `done` | `T.good` | Up to date |
| `error` | `T.bad` | Error |
| `demo` | `T.demo` | Demo |

### UpdatedAgo (app bar)

Цвет меняется в зависимости от возраста данных:
- ≤ 30 мин → `T.textSec` (нейтральный)
- > 30 мин → `T.warn` + dot
- > 2 ч → `T.bad` + dot
