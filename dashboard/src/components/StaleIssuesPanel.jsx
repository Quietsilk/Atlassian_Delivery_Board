import { useState } from "react";
import { font, radius, transition } from "../tokens";
import { useT } from "../context/ThemeContext";

function agingColor(T, days) {
  if (days >= 14) return T.bad;
  if (days >= 7)  return T.warn;
  return T.textMuted;
}

function agingBg(T, days) {
  if (days >= 14) return T.badBg;
  if (days >= 7)  return T.warnBg;
  return "transparent";
}

function agingBorder(T, days) {
  if (days >= 14) return T.badBdr;
  if (days >= 7)  return T.warnBdr;
  return T.border;
}

function initials(name) {
  if (!name) return "?";
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
}

export default function StaleIssuesPanel({ items = [], threshold = 5 }) {
  const T = useT();
  const [open, setOpen] = useState(false);

  const stale   = items.filter(i => i.daysInProgress >= threshold);
  const blocked = items.filter(i => i.blockedReason);
  const sorted  = [...items].sort((a, b) => b.daysInProgress - a.daysInProgress);
  const hasBadge = stale.length > 0 || blocked.length > 0;

  return (
    <div style={{
      background: T.bgCard,
      border: `1px solid ${hasBadge ? T.warnBdr : T.border}`,
      borderRadius: radius.panel, overflow: "hidden",
      transition: `border-color ${transition.normal}`,
      boxShadow: T.cardShadow,
    }}>
      <style>{`@keyframes fadeIn { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:translateY(0); } }`}</style>

      {/* ── Header ──────────────────────────────────────────────── */}
      <button type="button" onClick={() => setOpen(v => !v)} style={{
        width: "100%", background: "none", border: "none", cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 18px", gap: 12, fontFamily: "inherit",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: font.size.sm, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: T.textFaint }}>
            Stale Issues
          </span>
          <div style={{ display: "flex", gap: 5 }}>
            {stale.length > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 5, background: T.warnBg, border: `1px solid ${T.warnBdr}` }}>
                <span style={{ width: 4, height: 4, borderRadius: "50%", background: T.warn, display: "block" }} />
                <span style={{ fontSize: font.size.xs, fontWeight: 700, color: T.warn }}>{stale.length} aging</span>
              </div>
            )}
            {blocked.length > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 5, background: T.badBg, border: `1px solid ${T.badBdr}` }}>
                <span style={{ fontSize: font.size.xs, fontWeight: 700, color: T.bad }}>{blocked.length} blocked</span>
              </div>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: "0.7rem", color: T.textFaint }}>{items.length} tasks</span>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
            style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: `transform ${transition.normal}`, flexShrink: 0 }}>
            <path d="M3 5l4 4 4-4" stroke={T.textMuted} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </button>

      {/* ── Expanded list ────────────────────────────────────────── */}
      {open && (
        <div style={{ borderTop: `1px solid ${T.border}`, animation: `fadeIn ${transition.normal} ease` }}>
          {/* Legend */}
          <div style={{ padding: "7px 18px", borderBottom: `1px solid ${T.borderSub}`, display: "flex", alignItems: "center", gap: 14 }}>
            {[["≥14d", T.bad, "critical"], ["≥7d", T.warn, "aging"], ["<7d", T.textMuted, "ok"]].map(([label, clr, name]) => (
              <div key={name} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: clr }} />
                <span style={{ fontSize: "0.65rem", color: T.textFaint }}>{label} {name}</span>
              </div>
            ))}
          </div>

          {sorted.length === 0 && (
            <div style={{ padding: "18px", textAlign: "center", fontSize: "0.8rem", color: T.textFaint }}>
              No in-progress issues
            </div>
          )}

          {/* Rows */}
          {sorted.map((item, i) => (
            <div key={item.key + i} style={{
              display: "flex", alignItems: "flex-start", gap: 12,
              padding: "10px 18px",
              borderBottom: i < sorted.length - 1 ? `1px solid ${T.borderSub}` : "none",
              background: item.daysInProgress >= 14 ? T.badBg
                        : item.daysInProgress >= 7  ? T.warnBg
                        : "transparent",
            }}>
              {/* Age pill */}
              <div style={{
                flexShrink: 0, minWidth: 40,
                padding: "3px 8px", borderRadius: radius.sm, textAlign: "center", marginTop: 2,
                background: agingBg(T, item.daysInProgress),
                border: `1px solid ${agingBorder(T, item.daysInProgress)}`,
              }}>
                <span style={{ fontSize: font.size.sm, fontWeight: 700, color: agingColor(T, item.daysInProgress), fontFamily: font.family.mono }}>
                  {item.daysInProgress}d
                </span>
              </div>

              {/* Key + title + blocker */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                  <span style={{ fontSize: font.size.xs, color: T.brand, fontFamily: font.family.mono, fontWeight: 600, flexShrink: 0 }}>
                    {item.key}
                  </span>
                  <span style={{ fontSize: "0.65rem", padding: "1px 6px", borderRadius: 4, background: T.borderSub, color: T.textFaint, flexShrink: 0 }}>
                    {item.status}
                  </span>
                </div>
                <div style={{ fontSize: "0.8rem", color: T.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: item.blockedReason ? 4 : 0 }}>
                  {item.title || "—"}
                </div>
                {item.blockedReason && (
                  <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 3 }}>
                    <div style={{ width: 14, height: 14, borderRadius: 3, background: T.badBg, border: `1px solid ${T.badBdr}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <svg width="6" height="6" viewBox="0 0 6 6" fill="none">
                        <path d="M3 1v2.5M3 4.5v.5" stroke={T.bad} strokeWidth="1.2" strokeLinecap="round"/>
                      </svg>
                    </div>
                    <span style={{ fontSize: "0.7rem", color: T.bad, opacity: 0.75, fontStyle: "italic" }}>
                      {item.blockedReason}
                    </span>
                  </div>
                )}
              </div>

              {/* Assignee avatar */}
              {item.assignee && (
                <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 5, marginTop: 2 }}>
                  <div style={{ width: 22, height: 22, borderRadius: "50%", background: T.brandBg, border: `1px solid ${T.brandBdr}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.58rem", fontWeight: 700, color: T.brand }}>
                    {initials(item.assignee)}
                  </div>
                  <span style={{ fontSize: "0.7rem", color: T.textMuted }}>
                    {item.assignee.split(" ")[0]}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
