import { useState } from "react";

const TABS = ["summary", "risks", "actions"];
const HINTS = [
  "Low flow efficiency often indicates excessive queue wait time",
  "Reopened tasks can signal unclear acceptance criteria or QA gaps",
];

export default function AIPanel({ analysis, prominent }) {
  const [tab, setTab] = useState("summary");

  return (
    <div style={{
      background: prominent ? "rgba(79,124,255,0.06)" : "rgba(255,255,255,0.025)",
      border: `1px solid ${prominent ? "rgba(79,124,255,0.25)" : "rgba(255,255,255,0.07)"}`,
      borderRadius: 14, overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 18px 0", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: analysis ? "#4f7cff" : "rgba(255,255,255,0.2)",
            boxShadow: analysis ? "0 0 6px rgba(79,124,255,0.8)" : "none",
          }} />
          <span style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: analysis ? "rgba(79,124,255,0.9)" : "rgba(255,255,255,0.3)" }}>
            AI Insights
          </span>
        </div>
        {/* Tab bar — only shown when analysis is available */}
        {analysis && (
          <div style={{ display: "flex", gap: 2 }}>
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)} style={{
                padding: "5px 12px", border: "none", borderRadius: 6,
                background: tab === t ? "rgba(79,124,255,0.15)" : "transparent",
                color: tab === t ? "#4f7cff" : "rgba(255,255,255,0.35)",
                fontSize: "0.73rem", fontWeight: 600, cursor: "pointer",
                letterSpacing: "0.02em", transition: "all 0.15s", textTransform: "capitalize",
              }}>{t}</button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ padding: "14px 18px 16px", minHeight: 90 }}>
        {!analysis ? (
          <div>
            <p style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.25)", marginBottom: 10, fontStyle: "italic" }}>
              Sync to generate AI-powered insights for this project.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {HINTS.map((h, i) => (
                <div key={i} style={{ fontSize: "0.76rem", color: "rgba(255,255,255,0.22)", padding: "6px 10px", background: "rgba(255,255,255,0.03)", borderRadius: 6, borderLeft: "2px solid rgba(79,124,255,0.2)", lineHeight: 1.5 }}>{h}</div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {tab === "summary" && <p style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.78)", lineHeight: 1.75 }}>{analysis.summary}</p>}
            {tab === "risks" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {analysis.risks.map((r, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <div style={{ width: 18, height: 18, borderRadius: 4, background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                      <svg width="8" height="8" viewBox="0 0 8 8"><path d="M4 1v4M4 6.5v.5" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round"/></svg>
                    </div>
                    <span style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.72)", lineHeight: 1.6 }}>{r}</span>
                  </div>
                ))}
              </div>
            )}
            {tab === "actions" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {analysis.actions.map((a, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <div style={{ width: 18, height: 18, borderRadius: 4, background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.22)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                      <svg width="8" height="8" viewBox="0 0 8 8"><path d="M1.5 4.5l2 2 3-3.5" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg>
                    </div>
                    <span style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.72)", lineHeight: 1.6 }}>{a}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
