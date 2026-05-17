import { useState } from "react";
import { font, radius, transition, getStatusColors } from "../tokens";
import { useT } from "../context/ThemeContext";

function StatusBar({ value, max, clr, borderSub }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ height: 3, background: borderSub, borderRadius: 2, overflow: "hidden", marginTop: 2 }}>
      <div style={{ height: "100%", width: `${pct}%`, background: clr, borderRadius: 2, transition: transition.kpiBar }} />
    </div>
  );
}

export default function KpiCard({ label, sublabel, value, unit, delta, insight, status = "neutral", barMax, tooltip }) {
  const T  = useT();
  const sc = getStatusColors(T, status);
  const [hovered, setHovered] = useState(false);
  const pad = "16px 18px";
  const num = font.size.kpiLg;

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
        border: `1px solid ${hovered ? T.borderHi : sc.border}`,
        borderRadius: radius.card, padding: pad,
        display: "flex", flexDirection: "column", gap: 5,
        cursor: "default",
        transition: `border-color ${transition.normal}, background ${transition.normal}`,
        position: "relative", overflow: "hidden",
        boxShadow: T.cardShadow,
      }}
    >
      {/* Status stripe */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: sc.stripe,
        borderRadius: `${radius.card}px ${radius.card}px 0 0`,
        opacity: 0.85,
      }} />

      {/* Title */}
      <div>
        <div style={{
          fontSize: font.size.sm, fontWeight: font.weight.semibold,
          color: T.textLabel, textTransform: "uppercase",
          letterSpacing: font.tracking.wider,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>
          {label}
        </div>
        {sublabel && (
          <div style={{
            fontSize: font.size.xs, color: T.textFaint,
            marginTop: 1, fontFamily: font.family.mono,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {sublabel}
          </div>
        )}
      </div>

      {/* Value */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
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

      {/* Delta */}
      {delta && (
        <div style={{
          fontSize: font.size.xs, fontWeight: font.weight.medium,
          color: delta.good ? T.good : T.bad,
          fontFamily: font.family.mono,
        }}>
          {delta.text}
        </div>
      )}

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
