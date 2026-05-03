import { useState } from "react";
import Sparkline from "./Sparkline";

const STATUS_COLOR = { good: "#22c55e", warn: "#f59e0b", bad: "#ef4444", neutral: "rgba(255,255,255,0.15)" };
const STATUS_BG    = { good: "rgba(34,197,94,0.07)", warn: "rgba(245,158,11,0.07)", bad: "rgba(239,68,68,0.07)", neutral: "transparent" };

function StatusBar({ value, max, color }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ height: 3, background: "rgba(255,255,255,0.07)", borderRadius: 2, overflow: "hidden", marginTop: 2 }}>
      <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 2, transition: "width 0.6s ease" }} />
    </div>
  );
}

export default function KpiCard({ label, sublabel, value, unit, p85, delta, status = "neutral", history, lowerBetter, barMax, rich, compact, tooltip }) {
  const [hovered, setHovered] = useState(false);
  const c   = STATUS_COLOR[status];
  const bg  = STATUS_BG[status];
  const pad = compact ? "12px 14px" : "16px 18px";
  const num = compact ? "1.7rem"    : "2.1rem";

  return (
    <div
      title={tooltip}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? "rgba(255,255,255,0.035)" : bg,
        border: `1px solid ${hovered ? "rgba(255,255,255,0.12)" : (status !== "neutral" ? c + "40" : "rgba(255,255,255,0.07)")}`,
        borderRadius: 12, padding: pad,
        display: "flex", flexDirection: "column", gap: 6,
        cursor: "default", transition: "border-color 0.2s, background 0.2s",
        position: "relative", overflow: "hidden",
      }}
    >
      {/* Status stripe */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: status !== "neutral" ? c : "transparent",
        borderRadius: "12px 12px 0 0", opacity: 0.8,
      }} />

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.07em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</div>
          {sublabel && <div style={{ fontSize: "0.67rem", color: "rgba(255,255,255,0.28)", marginTop: 1, fontFamily: "'IBM Plex Mono', monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{sublabel}</div>}
        </div>
        {rich && history && <Sparkline values={history} lowerBetter={lowerBetter} />}
      </div>

      {/* Value */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginTop: "auto" }}>
        <span style={{ fontSize: num, fontWeight: 800, color: "#fff", letterSpacing: "-0.04em", fontFeatureSettings: '"tnum"', lineHeight: 1 }}>{value}</span>
        {unit && <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "rgba(255,255,255,0.4)", marginBottom: 1 }}>{unit}</span>}
        {delta && (
          <span style={{ fontSize: "0.72rem", fontWeight: 600, color: delta.good ? "#22c55e" : "#ef4444", marginLeft: 4, marginBottom: 2 }}>{delta.text}</span>
        )}
      </div>

      {/* P85 + bar */}
      {rich && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {p85 && <div style={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.28)", fontFamily: "'IBM Plex Mono', monospace" }}>P85 {p85}</div>}
          {barMax && <StatusBar value={parseFloat(value) || 0} max={barMax} color={c} />}
        </div>
      )}
    </div>
  );
}
