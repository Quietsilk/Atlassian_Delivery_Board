# Design System — AI Delivery Analyst

Единственный источник правды для цветов, типографики, отступов и анимаций.  
Файл: `src/tokens.js`

Поддерживаются две темы: **Dark (Calm)** и **Light**. Переключение — кнопка в шапке.

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
| `T.bg` | `#13151b` | `#f0f2f5` | root background |
| `T.bgBar` | `rgba(19,21,27,0.95)` | `rgba(244,246,249,0.95)` | app bar |
| `T.bgCard` | `#1c1f28` | `#ffffff` | KPI-карточки, AI-панель |
| `T.bgSidebar` | `rgba(0,0,0,0.20)` | `rgba(0,0,0,0.025)` | сайдбар |

### Brand

| Токен | Dark | Light | Назначение |
|---|---|---|---|
| `T.brand` | `#6b8cff` | `#4f6fe8` | акцент: кнопки, активные табы, AI-точка |
| `T.brandBg` | `rgba(107,140,255,0.08)` | `rgba(79,111,232,0.07)` | фон brand-элементов |
| `T.brandBdr` | `rgba(107,140,255,0.30)` | `rgba(79,111,232,0.25)` | рамка brand-элементов |
| `T.brandFocus` | `rgba(107,140,255,0.40)` | `rgba(79,111,232,0.35)` | border при :focus |
| `T.brandGlow` | `rgba(107,140,255,0.03)` | `rgba(79,111,232,0.04)` | bg при :focus |

### Статусы

| Токен | Dark | Light | Назначение |
|---|---|---|---|
| `T.good` / `T.goodBg` / `T.goodBdr` | `#4ade80` | `#16a34a` | позитивный |
| `T.warn` / `T.warnBg` / `T.warnBdr` | `#fbbf24` | `#b45309` | предупреждение |
| `T.bad` / `T.badBg` / `T.badBdr` | `#f87171` | `#dc2626` | критический |
| `T.demo` / `T.demoBg` / `T.demoBdr` | `#a78bfa` | `#7c3aed` | demo-данные |

**Правило:** `getStatusColors(T, status)` → `{ fg, bg, border, stripe }` — не писать switch/if.

### Текст

| Токен | Dark | Light | Назначение |
|---|---|---|---|
| `T.text` | `#dde1ea` | `#1a1d24` | основной текст, KPI-значения |
| `T.textSec` | `rgba(255,255,255,0.55)` | `rgba(0,0,0,0.55)` | вторичный текст |
| `T.textMuted` | `rgba(255,255,255,0.42)` | `rgba(0,0,0,0.40)` | field labels |
| `T.textFaint` | `rgba(255,255,255,0.30)` | `rgba(0,0,0,0.28)` | section labels, sparkline neutral |
| `T.textLabel` | `rgba(255,255,255,0.50)` | `rgba(0,0,0,0.45)` | заголовки KPI-карточек |

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
| `radius.sm` | 6 | маленькие кнопки, бейджи |
| `radius.md` | 7 | status pill, connect button |
| `radius.input` | 8 | все инпуты |
| `radius.card` | 12 | KPI-карточки |
| `radius.panel` | 14 | AI-панель, StaleIssuesPanel |

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
┌─ status stripe (2px top) ──────────────┐
│ LABEL                                   │
│ sublabel                                │
│                                         │
│ 4.2 d                                   │
│ -1.9d vs last          ← delta          │
│ 1 item >14d in progress ← insight       │
│ ████████░░░░  (progress bar)           │
└─────────────────────────────────────────┘
```

**Delta** — формат зависит от типа метрики:
- Flow (Cycle Time, TTM): `±Xd vs last` — скрывается если throughput < 5 или нет prev
- Snapshot (WIP, Backlog, Reopened): `+3 (−44%)` — абсолютное + относительное %
- Проценты (Flow Efficiency, Reopened Rate): `±X% vs last`

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
