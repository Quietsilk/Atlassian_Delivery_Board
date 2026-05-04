/**
 * AI Delivery Analyst — Design Tokens v2 (Calm)
 *
 * Single source of truth for colours, typography, spacing, radii and shadows.
 * Import into components instead of hardcoding magic strings.
 *
 * Usage:
 *   import { color, radius, font, statusColors } from "../tokens";
 *   style={{ background: color.surface.card, borderRadius: radius.card }}
 *
 * Colour philosophy (v2):
 * - Canvas warmer — #111318 instead of #0e1016
 * - Status colours muted — signal without shouting
 * - Cards monochrome by default; colour only in stripe, delta, badge
 * - Brand slate-blue instead of electric blue
 */

/* ─── Colour palette ──────────────────────────────────────────────────────── */

export const color = {
  /* Canvas — warmer, not pitch black */
  bg: "#111318",
  surface: {
    sidebar:   "rgba(255,255,255,0.018)",
    card:      "rgba(255,255,255,0.03)",
    cardHover: "rgba(255,255,255,0.042)",
    overlay:   "#1a1d24",
  },

  /* Borders — slightly more visible */
  border: {
    subtle:  "rgba(255,255,255,0.06)",
    default: "rgba(255,255,255,0.09)",
    strong:  "rgba(255,255,255,0.14)",
  },

  /* Brand — slate-blue, less electric */
  brand: {
    default: "#6b8cff",           // was #4f7cff
    bg:      "rgba(107,140,255,0.08)",
    bgHover: "rgba(107,140,255,0.14)",
    border:  "rgba(107,140,255,0.30)",
    focus:   "rgba(107,140,255,0.40)",
    glow:    "rgba(107,140,255,0.03)",
  },

  /* Status — good */
  good: {
    fg:         "#4ade80",        // was #22c55e — softer green
    bg:         "transparent",   // no coloured card bg in v2
    bgPill:     "rgba(74,222,128,0.07)",
    border:     "rgba(74,222,128,0.18)",
    borderPill: "rgba(74,222,128,0.12)",
    stripe:     "#4ade80",
    glow:       "rgba(74,222,128,0.55)",
  },

  /* Status — warn */
  warn: {
    fg:     "#fbbf24",            // was #f59e0b — lighter amber
    bg:     "transparent",
    bgPill: "rgba(251,191,36,0.07)",
    border: "rgba(251,191,36,0.18)",
    stripe: "#fbbf24",
  },

  /* Status — bad */
  bad: {
    fg:     "#f87171",            // was #ef4444 — rose instead of red
    bg:     "transparent",
    bgPill: "rgba(248,113,113,0.07)",
    border: "rgba(248,113,113,0.18)",
    stripe: "#f87171",
  },

  /* Status — neutral */
  neutral: {
    fg:     "rgba(255,255,255,0.18)",
    bg:     "transparent",
    border: "rgba(255,255,255,0.08)",
    stripe: "transparent",
  },

  /* Status — demo (purple) */
  demo: {
    fg:     "#a78bfa",
    bg:     "rgba(167,139,250,0.07)",
    border: "rgba(167,139,250,0.22)",
  },

  /* Text — slightly quieter */
  text: {
    primary:   "#dde1ea",         // was #e2e6ef
    secondary: "rgba(255,255,255,0.45)",
    muted:     "rgba(255,255,255,0.28)",
    faint:     "rgba(255,255,255,0.18)",
    label:     "rgba(255,255,255,0.40)",  // KPI card labels
    sublabel:  "rgba(255,255,255,0.24)",  // KPI card sublabels
  },
};

/* ─── Status helpers ──────────────────────────────────────────────────────── */

/** Returns { fg, bg, border, stripe } for a given status string */
export function statusColors(status) {
  const s = color;
  return {
    good:    { fg: s.good.fg,    bg: s.good.bg,    border: s.good.border,    stripe: s.good.stripe    },
    warn:    { fg: s.warn.fg,    bg: s.warn.bg,    border: s.warn.border,    stripe: s.warn.stripe    },
    bad:     { fg: s.bad.fg,     bg: s.bad.bg,     border: s.bad.border,     stripe: s.bad.stripe     },
    neutral: { fg: s.neutral.fg, bg: s.neutral.bg, border: s.neutral.border, stripe: s.neutral.stripe },
  }[status] ?? { fg: s.text.muted, bg: "transparent", border: s.border.subtle, stripe: "transparent" };
}

/* ─── Typography ──────────────────────────────────────────────────────────── */

export const font = {
  family: {
    sans: "'Inter', system-ui, sans-serif",
    mono: "'IBM Plex Mono', monospace",
  },
  size: {
    xxs:   "0.62rem",   // section labels
    xs:    "0.67rem",   // field labels, sublabels
    sm:    "0.72rem",   // secondary text, mono values
    base:  "0.78rem",   // inputs, body text
    md:    "0.82rem",   // risk/action items
    lg:    "0.88rem",   // logo
    kpiSm: "1.7rem",    // KPI value compact
    kpiLg: "2.1rem",    // KPI value comfortable
  },
  weight: {
    regular:   400,
    medium:    500,
    semibold:  600,
    bold:      700,
    extrabold: 800,
  },
  tracking: {
    tight:  "-0.04em",
    normal: "0",
    wide:   "0.03em",
    wider:  "0.07em",
    widest: "0.10em",
  },
};

/* ─── Spacing ─────────────────────────────────────────────────────────────── */

export const space = {
  1:  2,  2:  4,  3:  6,  4:  8,
  5: 10,  6: 12,  7: 14,  8: 16,
  9: 18, 10: 20, 12: 24, 14: 28, 16: 32,
};

/* ─── Border radius ───────────────────────────────────────────────────────── */

export const radius = {
  sm:    6,
  md:    7,
  input: 8,
  card:  12,
  panel: 14,
};

/* ─── Elevation ───────────────────────────────────────────────────────────── */

export const shadow = {
  overlay: "0 8px 32px rgba(0,0,0,0.45)",
  card:    "0 1px 3px rgba(0,0,0,0.3)",
};

/* ─── Animation ───────────────────────────────────────────────────────────── */

export const transition = {
  fast:    "0.15s ease",
  normal:  "0.20s ease",
  sidebar: "width 0.22s cubic-bezier(0.4,0,0.2,1)",
  kpiBar:  "width 0.60s ease",
};

/* ─── Layout ──────────────────────────────────────────────────────────────── */

export const layout = {
  sidebarWidth:  264,
  appBarHeight:   48,
  kpiColumns:      3,
  kpiGapComfy:    14,
  kpiGapCompact:  10,
};
