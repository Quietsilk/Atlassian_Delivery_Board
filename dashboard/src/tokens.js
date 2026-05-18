/**
 * Atlassian Delivery Board — Design Tokens v3
 * Atlassian-inspired Light + Dark theme support.
 *
 * Usage:
 *   import { getTokens, getStatusColors } from "../tokens";
 *   const T = getTokens(mode);  // mode: "dark" | "light"
 *   const sc = getStatusColors(T, status);  // { fg, bg, border, stripe }
 */

/* ─── Dark theme ──────────────────────────────────────────────────────────── */
const dark = {
  mode: "dark",

  bg:        "#0C111B",
  bgBar:     "#101828",
  bgSidebar: "#111827",
  bgCard:    "#182230",
  bgCardHov: "#1F2A3D",
  bgInput:   "#111827",
  bgOverlay: "#182230",

  border:    "#344054",
  borderHi:  "#475467",
  borderSub: "#263244",

  text:      "#F9FAFB",
  textSec:   "#D0D5DD",
  textMuted: "#98A2B3",
  textFaint: "#667085",
  textLabel: "#B3B9C4",

  brand:      "#579DFF",
  brandBg:    "rgba(87,157,255,0.14)",
  brandBdr:   "rgba(87,157,255,0.38)",
  brandFocus: "#85B8FF",
  brandGlow:  "rgba(87,157,255,0.10)",

  good:    "#57D9A3",
  goodBg:  "rgba(87,217,163,0.12)",
  goodBdr: "rgba(87,217,163,0.34)",

  warn:    "#F5CD47",
  warnBg:  "rgba(245,205,71,0.13)",
  warnBdr: "rgba(245,205,71,0.35)",

  bad:    "#F87168",
  badBg:  "rgba(248,113,104,0.14)",
  badBdr: "rgba(248,113,104,0.36)",

  demo:    "#9F8FEF",
  demoBg:  "rgba(159,143,239,0.13)",
  demoBdr: "rgba(159,143,239,0.36)",

  cardShadow:    "0 1px 1px rgba(0,0,0,0.24)",
  overlayShadow: "0 12px 28px rgba(0,0,0,0.38)",
};

/* ─── Light theme ─────────────────────────────────────────────────────────── */
const light = {
  mode: "light",

  bg:        "#F4F5F7",
  bgBar:     "#FFFFFF",
  bgSidebar: "#FAFBFC",
  bgCard:    "#ffffff",
  bgCardHov: "#F7F8F9",
  bgInput:   "#ffffff",
  bgOverlay: "#ffffff",

  border:    "#DFE1E6",
  borderHi:  "#B3BAC5",
  borderSub: "#EBECF0",

  text:      "#172B4D",
  textSec:   "#42526E",
  textMuted: "#6B778C",
  textFaint: "#8993A4",
  textLabel: "#42526E",

  brand:      "#0052CC",
  brandBg:    "#DEEBFF",
  brandBdr:   "#B3D4FF",
  brandFocus: "#4C9AFF",
  brandGlow:  "#F4F8FF",

  good:    "#00875A",
  goodBg:  "#E3FCEF",
  goodBdr: "#ABF5D1",

  warn:    "#974F0C",
  warnBg:  "#FFF0B3",
  warnBdr: "#FFE380",

  bad:    "#DE350B",
  badBg:  "#FFEBE6",
  badBdr: "#FFBDAD",

  demo:    "#6554C0",
  demoBg:  "#EAE6FF",
  demoBdr: "#C0B6F2",

  cardShadow:    "0 1px 1px rgba(9,30,66,0.13)",
  overlayShadow: "0 8px 24px rgba(9,30,66,0.18)",
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
  tracking: { tight:"0", normal:"0", wide:"0.03em", wider:"0.07em", widest:"0.10em" },
};

/* ─── Radii ───────────────────────────────────────────────────────────────── */
export const radius = { sm:3, md:4, input:3, card:4, panel:4 };

/* ─── Animation ───────────────────────────────────────────────────────────── */
export const transition = {
  fast:    "0.15s ease",
  normal:  "0.20s ease",
  sidebar: "width 0.22s cubic-bezier(0.4,0,0.2,1)",
  kpiBar:  "width 0.60s ease",
};
