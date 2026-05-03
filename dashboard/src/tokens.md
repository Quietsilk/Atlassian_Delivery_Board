# Design System — AI Delivery Analyst

Единственный источник правды для цветов, типографики, отступов и радиусов.  
Файл: `src/tokens.js` — импортировать в компоненты, не дублировать строки.

---

## Цвета

### Canvas
| Токен | Значение | Применение |
|---|---|---|
| `color.bg` | `#0e1016` | root background |
| `color.surface.sidebar` | `rgba(255,255,255,0.016)` | фон сайдбара |
| `color.surface.card` | `rgba(255,255,255,0.025)` | KPI-карточки, AI-панель |
| `color.surface.overlay` | `#16181f` | tweaks panel, dropdown |

### Brand (blue)
| Токен | Применение |
|---|---|
| `color.brand.default` `#4f7cff` | акцентный цвет, активные табы, AI-точка |
| `color.brand.bg` | фон кнопки Connect, активного таба |
| `color.brand.border` | рамка кнопки Connect |
| `color.brand.focus` | border-color при :focus на инпутах |
| `color.brand.glow` | background при :focus на инпутах |

### Статусы KPI
| Статус | fg | bg | Применение |
|---|---|---|---|
| `good` | `#22c55e` | `rgba(34,197,94,0.07)` | Cycle Time ≤ 3d, Flow ≥ 40% … |
| `warn` | `#f59e0b` | `rgba(245,158,11,0.07)` | промежуточные значения |
| `bad`  | `#ef4444` | `rgba(239,68,68,0.07)`  | критические значения |
| `neutral` | `rgba(255,255,255,0.15)` | `transparent` | нет данных |
| `demo` | `#a78bfa` | `rgba(167,139,250,0.08)` | статус-пилюля Demo |

**Правило:** `statusColors(status)` возвращает `{ fg, bg, border }` — использовать вместо switch/if.

### Текст
| Токен | Значение | Применение |
|---|---|---|
| `color.text.primary` | `#e2e6ef` | основной текст, значения KPI |
| `color.text.secondary` | `rgba(255,255,255,0.50)` | хост в status pill |
| `color.text.muted` | `rgba(255,255,255,0.30)` | field labels, show/hide кнопка |
| `color.text.faint` | `rgba(255,255,255,0.22)` | section labels |
| `color.text.label` | `rgba(255,255,255,0.45)` | заголовки KPI-карточек |

---

## Типографика

### Размеры (font.size)
| Токен | rem | Применение |
|---|---|---|
| `xxs` | 0.62rem | section labels (JIRA CONNECTION) |
| `xs` | 0.67rem | field labels, sublabels KPI |
| `sm` | 0.72rem | mono-значения, вторичный текст |
| `base` | 0.78rem | инпуты, основной текст |
| `md` | 0.82rem | risk/action items в AIPanel |
| `lg` | 0.88rem | логотип |
| `kpiSm` | 1.7rem | значение KPI в compact-режиме |
| `kpiLg` | 2.1rem | значение KPI в comfortable-режиме |

### Шрифты
- **Sans**: `Inter, system-ui` — весь UI
- **Mono**: `IBM Plex Mono` — JQL, P85, sparkline sublabels

### Веса
`400 regular` / `500 medium` / `600 semibold` / `700 bold` / `800 extrabold`  
Значения KPI — `800`. Section labels — `700`. Field labels — `600`.

---

## Радиусы

| Токен | px | Применение |
|---|---|---|
| `radius.sm` | 6 | кнопки tweaks panel |
| `radius.md` | 7 | status pill, connect button |
| `radius.input` | 8 | все инпуты |
| `radius.card` | 12 | KPI-карточки |
| `radius.panel` | 14 | AI-панель |

---

## Компоненты

### KpiCard

**Структура:**
```
┌─ status stripe (2px top) ──────────────┐
│ LABEL              [sparkline]          │
│ sublabel                                │
│                                         │
│ 4.2 d  -20.8%                          │
│ P85 7.1d                                │
│ ████████░░░░  (progress bar)           │
└─────────────────────────────────────────┘
```

**Состояния:**
- `good` — зелёная stripe + `rgba(34,197,94,0.07)` фон
- `warn` — янтарная stripe
- `bad` — красная stripe
- `neutral` — без stripe, прозрачный фон

**Do:** передавать `tooltip` с определением метрики  
**Don't:** рендерить со статусом `bad` без `delta` — нет контекста динамики

---

### AIPanel

**Структура:**
```
● AI INSIGHTS         [Summary] [Risks] [Actions]  ← только если analysis ≠ null
────────────────────────────────────────────────
  <текст таба>
```

**Do:** показывать таб-бар только когда `analysis !== null`  
**Don't:** рендерить пустые табы Risks/Actions без массивов — `.map()` упадёт

---

### Sidebar — поля ввода

**Focus ring:** `border-color: color.brand.focus` + `background: color.brand.glow`  
**Blur:** возврат к `color.border.default` + `color.surface.card`  

**API Token:** Show/Hide кнопка внутри поля (slot-паттерн), `paddingRight: 44`  
**Connect:** два состояния — `disconnected` (синий) / `connected` (зелёный + ✓)  
**Status pill:** показывается только когда `connected && host` — домен без `https://`

---

### Кнопки

| Вариант | Border | Background | Color |
|---|---|---|---|
| Primary (Connect) | `brand.border` | `brand.bg` | `text.primary` |
| Connected | `good.border` | `good.bgPill` | `good.fg` |
| Ghost (Demo) | `border.default` | transparent | `text.muted` |
| Ghost hover | `border.strong` | `rgba(255,255,255,0.03)` | `text.secondary` |
| Tweaks active | `brand.border` | `brand.bg` | `brand.default` |
| Tweaks inactive | `border.default` | transparent | `text.muted` |

---

### Status Pill (app bar)

| State | Color | Label |
|---|---|---|
| `idle` | `text.muted` | Idle |
| `syncing` | `warn.fg` | Syncing… + spinner |
| `done` | `good.fg` | Up to date |
| `error` | `bad.fg` | Error |
| `demo` | `demo.fg` | Demo |

---

## Известные ограничения

- Все стили сейчас inline в JSX. Токены из `tokens.js` нужно подключать вручную при редактировании компонентов — авто-рефакторинг не делался.
- Тёмная тема единственная. `color.bg = #0e1016` хардкод.
- `autoSyncStale` не реализован — данные обновляются только вручную.
