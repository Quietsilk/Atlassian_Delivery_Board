import { useState } from "react";
import { font, radius, transition } from "../tokens";
import { useT } from "../context/ThemeContext";

const TABS = ["summary", "risks", "actions"];
const HINTS = [
  "Low flow efficiency often indicates excessive queue wait time",
  "Reopened tasks can signal unclear acceptance criteria or QA gaps",
];

export default function AIPanel({ analysis, prominent }) {
  const T = useT();
  const [tab, setTab] = useState("summary");

  return (
    <div style={{
      background: prominent ? T.brandBg : T.bgCard,
      border: `1px solid ${prominent ? T.brandBdr : T.border}`,
      borderRadius: radius.panel, overflow: "hidden",
      boxShadow: T.cardShadow,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 18px 0", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: analysis ? T.brand : T.textFaint,
            boxShadow: analysis ? `0 0 6px ${T.brandFocus}` : "none",
          }} />
          <span style={{ fontSize: font.size.sm, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: analysis ? T.brand : T.textMuted }}>
            AI Insights
          </span>
        </div>
        {analysis && (
          <div style={{ display: "flex", gap: 2 }}>
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)} style={{
                padding: "5px 12px", border: "none", borderRadius: radius.sm,
                background: tab === t ? T.brandBg : "transparent",
                color: tab === t ? T.brand : T.textMuted,
                fontSize: "0.73rem", fontWeight: 600, cursor: "pointer",
                letterSpacing: "0.02em", transition: `all ${transition.fast}`, textTransform: "capitalize",
              }}>{t}</button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ padding: "14px 18px 16px", minHeight: 90 }}>
        {!analysis ? (
          <div>
            <p style={{ fontSize: font.size.md, color: T.textFaint, marginBottom: 10, fontStyle: "italic" }}>
              Sync to generate AI-powered insights for this project.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {HINTS.map((h, i) => (
                <div key={i} style={{ fontSize: "0.76rem", color: T.textFaint, padding: "6px 10px", background: T.bgCard, borderRadius: radius.sm, borderLeft: `2px solid ${T.brandBg}`, lineHeight: 1.5 }}>{h}</div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {tab === "summary" && <p style={{ fontSize: "0.85rem", color: T.textSec, lineHeight: 1.75 }}>{analysis.summary}</p>}
            {tab === "risks" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {analysis.risks.map((r, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <div style={{ width: 18, height: 18, borderRadius: 4, background: T.badBg, border: `1px solid ${T.badBdr}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                      <svg width="8" height="8" viewBox="0 0 8 8"><path d="M4 1v4M4 6.5v.5" stroke={T.bad} strokeWidth="1.5" strokeLinecap="round"/></svg>
                    </div>
                    <span style={{ fontSize: font.size.md, color: T.textSec, lineHeight: 1.6 }}>{r}</span>
                  </div>
                ))}
              </div>
            )}
            {tab === "actions" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {analysis.actions.map((a, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <div style={{ width: 18, height: 18, borderRadius: 4, background: T.goodBg, border: `1px solid ${T.goodBdr}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                      <svg width="8" height="8" viewBox="0 0 8 8"><path d="M1.5 4.5l2 2 3-3.5" stroke={T.good} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg>
                    </div>
                    <span style={{ fontSize: font.size.md, color: T.textSec, lineHeight: 1.6 }}>{a}</span>
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
