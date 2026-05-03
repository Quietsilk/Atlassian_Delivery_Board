/**
 * AI Delivery Analyst — Design Tokens
 *
 * Single source of truth for colours, typography, spacing, radii and shadows.
 * Import into components instead of hardcoding magic strings.
 *
 * Usage:
 *   import { color, radius, font } from "../tokens";
 *   style={{ background: color.surface.card, borderRadius: radius.card }}
 */

/* ─── Colour palette ──────────────────────────────────────────────────────── */

export const color = {
  /* Canvas */
  bg:      "#0e1016",   // root background
  surface: {
    sidebar: "rgba(255,255,255,0.016)",
    card:    "rgba(255,255,255,0.025)",
    cardHover: "rgba(255,255,255,0.035)",
    overlay: "#16181f",  // tweaks panel, dropdowns
  },

  /* Borders */
  border: {
    subtle:  "rgba(255,255,255,0.05)",
    default: "rgba(255,255,255,0.08)",
    strong:  "rgba(255,255,255,0.12)",
  },

  /* Brand — blue accent */
  brand: {
    default: "#4f7cff",
    bg:      "rgba(79,124,255,0.10)",
    bgHover: "rgba(79,124,255,0.20)",
    border:  "rgba(79,124,255,0.40)",
    focus:   "rgba(79,124,255,0.50)",
    glow:    "rgba(79,124,255,0.04)",  // input focus bg
  },

  /* Status — good */
  good: {
    fg:     "#22c55e",
    bg:     "rgba(34,197,94,0.07)",
    bgPill: "rgba(34,197,94,0.06)",
    border: "rgba(34,197,94,0.22)",
    borderPill: "rgba(34,197,94,0.12)",
    glow:   "rgba(34,197,94,0.70)",
  },

  /* Status — warn */
  warn: {
    fg:     "#f59e0b",
    bg:     "rgba(245,158,11,0.07)",
    border: "rgba(245,158,11,0.25)",
  },

  /* Status — bad */
  bad: {
    fg:     "#ef4444",
    bg:     "rgba(239,68,68,0.07)",
    border: "rgba(239,68,68,0.25)",
  },

  /* Status — demo (purple) */
  demo: {
    fg:     "#a78bfa",
    bg:     "rgba(167,139,250,0.08)",
    border: "rgba(167,139,250,0.30)",
  },

  /* Text */
  text: {
    primary:   "#e2e6ef",           // main content
    secondary: "rgba(255,255,255,0.50)",
    muted:     "rgba(255,255,255,0.30)",
    faint:     "rgba(255,255,255,0.22)",
    label:     "rgba(255,255,255,0.45)",  // KPI card labels
    sublabel:  "rgba(255,255,255,0.28)",  // KPI card sublabels
  },
};

/* ─── Status helpers ──────────────────────────────────────────────────────── */

/** Returns { fg, bg, border } for a given status string */
export function statusColors(status) {
  return {
    good:    { fg: color.good.fg,    bg: color.good.bg,    border: color.good.border },
    warn:    { fg: color.warn.fg,    bg: color.warn.bg,    border: color.warn.border },
    bad:     { fg: color.bad.fg,     bg: color.bad.bg,     border: color.bad.border },
    neutral: { fg: "rgba(255,255,255,0.15)", bg: "transparent", border: "rgba(255,255,255,0.07)" },
  }[status] ?? { fg: color.text.muted, bg: "transparent", border: color.border.subtle };
}

/* ─── Typography ──────────────────────────────────────────────────────────── */

export const font = {
  family: {
    sans: "'Inter', system-ui, sans-serif",
    mono: "'IBM Plex Mono', monospace",
  },
  size: {
    xxs:  "0.62rem",   // section labels (JIRA CONNECTION)
    xs:   "0.67rem",   // field labels, sublabels
    sm:   "0.72rem",   // secondary text, mono values
    base: "0.78rem",   // inputs, body text
    md:   "0.82rem",   // risk/action items
    lg:   "0.88rem",   // logo
    kpiSm: "1.7rem",   // KPI value compact
    kpiLg: "2.1rem",   // KPI value comfortable
  },
  weight: {
    regular:  400,
    medium:   500,
    semibold: 600,
    bold:     700,
    extrabold: 800,
  },
  tracking: {
    tight:   "-0.04em",
    normal:  "0",
    wide:    "0.03em",
    wider:   "0.07em",
    widest:  "0.10em",  // section labels
  },
};

/* ─── Spacing ─────────────────────────────────────────────────────────────── */

export const space = {
  1:  2,
  2:  4,
  3:  6,
  4:  8,
  5: 10,
  6: 12,
  7: 14,
  8: 16,
  9: 18,
 10: 20,
 12: 24,
 14: 28,
 16: 32,
};

/* ─── Border radius ───────────────────────────────────────────────────────── */

export const radius = {
  sm:     6,   // buttons in tweaks panel, small badges
  md:     7,   // connect button, status pill
  input:  8,   // form inputs
  card:  12,   // KPI cards
  panel: 14,   // AI panel, large cards
};

/* ─── Elevation / shadows ─────────────────────────────────────────────────── */

export const shadow = {
  overlay: "0 8px 32px rgba(0,0,0,0.5)",  // tweaks panel
};

/* ─── Animation ───────────────────────────────────────────────────────────── */

export const transition = {
  fast:   "0.15s ease",
  normal: "0.20s ease",
  sidebar: "width 0.22s cubic-bezier(0.4,0,0.2,1)",
  kpiBar:  "width 0.60s ease",
};

/* ─── Layout ──────────────────────────────────────────────────────────────── */

export const layout = {
  sidebarWidth: 264,   // px
  appBarHeight:  48,   // px
  kpiColumns:     3,   // grid columns
  kpiGapComfy:   14,   // px gap comfortable
  kpiGapCompact: 10,   // px gap compact
};
