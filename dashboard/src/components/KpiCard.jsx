import { useState } from "react";
import { font, radius, transition, getStatusColors } from "../tokens";
import { useT } from "../context/ThemeContext";

function StatusBar({ value, max, clr, borderSub }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ height: 4, background: borderSub, borderRadius: 999, overflow: "hidden", marginTop: 4 }}>
      <div style={{ height: "100%", width: `${pct}%`, background: clr, borderRadius: 999, transition: transition.kpiBar }} />
    </div>
  );
}

export default function KpiCard({ label, sublabel, value, unit, delta, insight, status = "neutral", barMax, tooltip }) {
  const T  = useT();
  const sc = getStatusColors(T, status);
  const [hovered, setHovered] = useState(false);
  const pad = "12px 14px";
  const num = "1.72rem";

  const insightColor = insight?.level === "bad"  ? T.bad
                     : insight?.level === "warn" ? T.warn
                     : T.textMuted;

  return (
    <div
      title={tooltip}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? T.bgCardHov : T.bgCard,
        border: `1px solid ${hovered ? T.borderHi : T.border}`,
        borderRadius: radius.card, padding: pad,
        display: "flex", flexDirection: "column", gap: 8,
        cursor: "default",
        transition: `border-color ${transition.normal}, background ${transition.normal}, box-shadow ${transition.normal}`,
        position: "relative", overflow: "hidden",
        boxShadow: hovered ? T.overlayShadow : T.cardShadow,
      }}
    >
      {/* Title */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
        <div style={{ minWidth: 0 }}>
        <div style={{
          fontSize: font.size.base, fontWeight: font.weight.bold,
          color: T.text,
          letterSpacing: font.tracking.normal,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>
          {label}
        </div>
        {sublabel && (
          <div style={{
            fontSize: font.size.xs, color: T.textMuted,
            marginTop: 1, fontFamily: font.family.mono,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {sublabel}
          </div>
        )}
        </div>
        <span style={{
          flexShrink: 0,
          padding: "2px 6px",
          borderRadius: radius.sm,
          background: sc.bg,
          border: `1px solid ${sc.border}`,
          color: sc.fg,
          fontSize: "0.58rem",
          fontWeight: font.weight.bold,
          textTransform: "uppercase",
          letterSpacing: font.tracking.wide,
        }}>
          {status}
        </span>
      </div>

      {/* Value */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 4, minWidth: 0 }}>
        <span style={{
          fontSize: num, fontWeight: font.weight.extrabold,
          color: T.text, letterSpacing: font.tracking.tight,
          fontFeatureSettings: '"tnum"', lineHeight: 1,
        }}>
          {value}
        </span>
        {unit && (
          <span style={{ fontSize: "0.9rem", fontWeight: font.weight.semibold, color: T.textLabel, marginBottom: 1 }}>
            {unit}
          </span>
        )}
        </div>
        {delta && (
          <span style={{
            fontSize: font.size.xs, fontWeight: font.weight.semibold,
            color: delta.good ? T.good : T.bad,
            fontFamily: font.family.mono,
            whiteSpace: "nowrap",
          }}>
            {delta.text}
          </span>
        )}
      </div>

      {/* Insight */}
      {insight && (
        <div style={{
          fontSize: font.size.xs,
          color: insightColor,
          lineHeight: 1.4,
        }}>
          {insight.text}
        </div>
      )}

      {/* Status bar */}
      {barMax != null && (
        <StatusBar value={parseFloat(value) || 0} max={barMax} clr={sc.fg} borderSub={T.borderSub} />
      )}
    </div>
  );
}
