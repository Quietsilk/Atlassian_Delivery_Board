import { useState } from "react";
import { color, font, radius, transition, statusColors } from "../tokens";
import Sparkline from "./Sparkline";

function StatusBar({ value, max, clr }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ height: 3, background: color.border.subtle, borderRadius: 2, overflow: "hidden", marginTop: 2 }}>
      <div style={{ height: "100%", width: `${pct}%`, background: clr, borderRadius: 2, transition: transition.kpiBar }} />
    </div>
  );
}

export default function KpiCard({ label, sublabel, value, unit, p85, delta, status = "neutral", history, lowerBetter, barMax, rich, compact, tooltip }) {
  const [hovered, setHovered] = useState(false);
  const sc  = statusColors(status);
  const pad = compact ? "12px 14px" : "16px 18px";
  const num = compact ? font.size.kpiSm : font.size.kpiLg;

  return (
    <div
      title={tooltip}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? color.surface.cardHover : color.surface.card,
        border: `1px solid ${hovered ? color.border.strong : sc.border}`,
        borderRadius: radius.card, padding: pad,
        display: "flex", flexDirection: "column", gap: 6,
        cursor: "default", transition: `border-color ${transition.normal}, background ${transition.normal}`,
        position: "relative", overflow: "hidden",
      }}
    >
      {/* Status stripe — 2px top accent, colour only here */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: sc.stripe,
        borderRadius: `${radius.card}px ${radius.card}px 0 0`,
        opacity: 0.85,
      }} />

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: font.size.sm, fontWeight: font.weight.semibold,
            color: color.text.label, textTransform: "uppercase",
            letterSpacing: font.tracking.wider,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {label}
          </div>
          {sublabel && (
            <div style={{
              fontSize: font.size.xs, color: color.text.sublabel,
              marginTop: 1, fontFamily: font.family.mono,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>
              {sublabel}
            </div>
          )}
        </div>
        {rich && history && <Sparkline values={history} lowerBetter={lowerBetter} />}
      </div>

      {/* Value row */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginTop: "auto" }}>
        <span style={{
          fontSize: num, fontWeight: font.weight.extrabold,
          color: "#fff", letterSpacing: font.tracking.tight,
          fontFeatureSettings: '"tnum"', lineHeight: 1,
        }}>
          {value}
        </span>
        {unit && (
          <span style={{ fontSize: "0.9rem", fontWeight: font.weight.semibold, color: color.text.label, marginBottom: 1 }}>
            {unit}
          </span>
        )}
        {delta && (
          <span style={{
            fontSize: font.size.sm, fontWeight: font.weight.semibold,
            color: delta.good ? color.good.fg : color.bad.fg,
            marginLeft: 4, marginBottom: 2,
          }}>
            {delta.text}
          </span>
        )}
      </div>

      {/* P85 + status bar */}
      {rich && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {p85 && (
            <div style={{ fontSize: "0.68rem", color: color.text.sublabel, fontFamily: font.family.mono }}>
              P85 {p85}
            </div>
          )}
          {barMax && <StatusBar value={parseFloat(value) || 0} max={barMax} clr={sc.fg} />}
        </div>
      )}
    </div>
  );
}
