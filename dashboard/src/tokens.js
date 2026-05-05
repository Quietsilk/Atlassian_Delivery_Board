/**
 * AI Delivery Analyst — Design Tokens v2
 * Dark (Calm) + Light theme support.
 *
 * Usage:
 *   import { getTokens, getStatusColors } from "../tokens";
 *   const T = getTokens(mode);  // mode: "dark" | "light"
 *   const sc = getStatusColors(T, status);  // { fg, bg, border, stripe }
 */

/* ─── Dark theme (Calm) ───────────────────────────────────────────────────── */
const dark = {
  mode: "dark",

  bg:        "#13151b",
  bgBar:     "rgba(19,21,27,0.95)",
  bgSidebar: "rgba(0,0,0,0.20)",
  bgCard:    "#1c1f28",
  bgCardHov: "#1f2230",
  bgInput:   "rgba(0,0,0,0.25)",
  bgOverlay: "#1c1f28",

  border:    "rgba(255,255,255,0.11)",
  borderHi:  "rgba(255,255,255,0.18)",
  borderSub: "rgba(255,255,255,0.07)",

  text:      "#dde1ea",
  textSec:   "rgba(255,255,255,0.55)",
  textMuted: "rgba(255,255,255,0.42)",
  textFaint: "rgba(255,255,255,0.30)",
  textLabel: "rgba(255,255,255,0.50)",

  brand:      "#6b8cff",
  brandBg:    "rgba(107,140,255,0.08)",
  brandBdr:   "rgba(107,140,255,0.30)",
  brandFocus: "rgba(107,140,255,0.40)",
  brandGlow:  "rgba(107,140,255,0.03)",

  good:    "#4ade80",
  goodBg:  "rgba(74,222,128,0.07)",
  goodBdr: "rgba(74,222,128,0.18)",

  warn:    "#fbbf24",
  warnBg:  "rgba(251,191,36,0.07)",
  warnBdr: "rgba(251,191,36,0.18)",

  bad:    "#f87171",
  badBg:  "rgba(248,113,113,0.07)",
  badBdr: "rgba(248,113,113,0.18)",

  demo:    "#a78bfa",
  demoBg:  "rgba(167,139,250,0.07)",
  demoBdr: "rgba(167,139,250,0.22)",

  cardShadow:    "0 1px 4px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.25)",
  overlayShadow: "0 8px 32px rgba(0,0,0,0.45)",
};

/* ─── Light theme ─────────────────────────────────────────────────────────── */
const light = {
  mode: "light",

  bg:        "#f0f2f5",
  bgBar:     "rgba(244,246,249,0.95)",
  bgSidebar: "rgba(0,0,0,0.025)",
  bgCard:    "#ffffff",
  bgCardHov: "#f8f9fb",
  bgInput:   "#ffffff",
  bgOverlay: "#ffffff",

  border:    "rgba(0,0,0,0.09)",
  borderHi:  "rgba(0,0,0,0.15)",
  borderSub: "rgba(0,0,0,0.06)",

  text:      "#1a1d24",
  textSec:   "rgba(0,0,0,0.55)",
  textMuted: "rgba(0,0,0,0.40)",
  textFaint: "rgba(0,0,0,0.28)",
  textLabel: "rgba(0,0,0,0.45)",

  brand:      "#4f6fe8",
  brandBg:    "rgba(79,111,232,0.07)",
  brandBdr:   "rgba(79,111,232,0.25)",
  brandFocus: "rgba(79,111,232,0.35)",
  brandGlow:  "rgba(79,111,232,0.04)",

  good:    "#16a34a",
  goodBg:  "rgba(22,163,74,0.07)",
  goodBdr: "rgba(22,163,74,0.20)",

  warn:    "#b45309",
  warnBg:  "rgba(180,83,9,0.07)",
  warnBdr: "rgba(180,83,9,0.20)",

  bad:    "#dc2626",
  badBg:  "rgba(220,38,38,0.07)",
  badBdr: "rgba(220,38,38,0.20)",

  demo:    "#7c3aed",
  demoBg:  "rgba(124,58,237,0.07)",
  demoBdr: "rgba(124,58,237,0.22)",

  cardShadow:    "0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04)",
  overlayShadow: "0 8px 32px rgba(0,0,0,0.15)",
};

/* ─── Status helpers (mode-aware) ─────────────────────────────────────────── */

/** getStatusColors(T, status) → { fg, bg, border, stripe } */
export function getStatusColors(T, status) {
  return {
    good:    { fg: T.good,     bg: T.goodBg, border: T.goodBdr, stripe: T.good    },
    warn:    { fg: T.warn,     bg: T.warnBg, border: T.warnBdr, stripe: T.warn    },
    bad:     { fg: T.bad,      bg: T.badBg,  border: T.badBdr,  stripe: T.bad     },
    neutral: { fg: T.textFaint, bg: "transparent", border: T.border, stripe: "transparent" },
  }[status] ?? { fg: T.textMuted, bg: "transparent", border: T.border, stripe: "transparent" };
}

/* ─── Main export ─────────────────────────────────────────────────────────── */

export function getTokens(mode) {
  return mode === "light" ? light : dark;
}

/* ─── Typography ──────────────────────────────────────────────────────────── */
export const font = {
  family: { sans: "'Inter', system-ui, sans-serif", mono: "'IBM Plex Mono', monospace" },
  size: { xxs:"0.62rem", xs:"0.67rem", sm:"0.72rem", base:"0.78rem", md:"0.82rem", lg:"0.88rem", kpiSm:"1.7rem", kpiLg:"2.1rem" },
  weight: { regular:400, medium:500, semibold:600, bold:700, extrabold:800 },
  tracking: { tight:"-0.04em", normal:"0", wide:"0.03em", wider:"0.07em", widest:"0.10em" },
};

/* ─── Radii ───────────────────────────────────────────────────────────────── */
export const radius = { sm:6, md:7, input:8, card:12, panel:14 };

/* ─── Animation ───────────────────────────────────────────────────────────── */
export const transition = {
  fast:    "0.15s ease",
  normal:  "0.20s ease",
  sidebar: "width 0.22s cubic-bezier(0.4,0,0.2,1)",
  kpiBar:  "width 0.60s ease",
};
