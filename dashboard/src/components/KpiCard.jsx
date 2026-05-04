import { useState } from "react";
import { font, radius, transition, getStatusColors } from "../tokens";
import { useT } from "../context/ThemeContext";
import Sparkline from "./Sparkline";

function StatusBar({ value, max, clr, borderSub }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ height: 3, background: borderSub, borderRadius: 2, overflow: "hidden", marginTop: 2 }}>
      <div style={{ height: "100%", width: `${pct}%`, background: clr, borderRadius: 2, transition: transition.kpiBar }} />
    </div>
  );
}

export default function KpiCard({ label, sublabel, value, unit, p85, delta, status = "neutral", history, lowerBetter, barMax, rich, compact, tooltip }) {
  const T   = useT();
  const sc  = getStatusColors(T, status);
  const [hovered, setHovered] = useState(false);
  const pad = compact ? "12px 14px" : "16px 18px";
  const num = compact ? font.size.kpiSm : font.size.kpiLg;

  return (
    <div
      title={tooltip}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? T.bgCardHov : T.bgCard,
        border: `1px solid ${hovered ? T.borderHi : sc.border}`,
        borderRadius: radius.card, padding: pad,
        display: "flex", flexDirection: "column", gap: 6,
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

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
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
        {rich && history && <Sparkline values={history} lowerBetter={lowerBetter} />}
      </div>

      {/* Value row */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginTop: "auto" }}>
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
        {delta && (
          <span style={{
            fontSize: font.size.sm, fontWeight: font.weight.semibold,
            color: delta.good ? T.good : T.bad,
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
            <div style={{ fontSize: "0.68rem", color: T.textFaint, fontFamily: font.family.mono }}>
              P85 {p85}
            </div>
          )}
          {barMax && <StatusBar value={parseFloat(value) || 0} max={barMax} clr={sc.fg} borderSub={T.borderSub} />}
        </div>
      )}
    </div>
  );
}
