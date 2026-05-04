import { useState } from "react";

const C = {
  red:      "#ef4444", redBg:   "rgba(239,68,68,0.08)",  redBorder:   "rgba(239,68,68,0.2)",
  amber:    "#f59e0b", amberBg: "rgba(245,158,11,0.08)", amberBorder: "rgba(245,158,11,0.2)",
  blue:     "#4f7cff",
  surface:  "rgba(255,255,255,0.025)",
  border:   "rgba(255,255,255,0.07)",
  text:     "#e2e6ef",
  muted:    "rgba(255,255,255,0.35)",
  dim:      "rgba(255,255,255,0.22)",
};

function agingColor(days) {
  if (days >= 14) return C.red;
  if (days >= 7)  return C.amber;
  return C.muted;
}

function agingBg(days) {
  if (days >= 14) return C.redBg;
  if (days >= 7)  return C.amberBg;
  return "transparent";
}

function agingBorder(days) {
  if (days >= 14) return C.redBorder;
  if (days >= 7)  return C.amberBorder;
  return C.border;
}

function initials(name) {
  if (!name) return "?";
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
}

export default function StaleIssuesPanel({ items = [], threshold = 5 }) {
  const [open, setOpen] = useState(false);

  const stale   = items.filter(i => i.daysInProgress >= threshold);
  const blocked = items.filter(i => i.blockedReason);
  const sorted  = [...items].sort((a, b) => b.daysInProgress - a.daysInProgress);

  const hasBadge = stale.length > 0 || blocked.length > 0;

  return (
    <div style={{
      background: C.surface,
      border: `1px solid ${hasBadge ? C.amberBorder : C.border}`,
      borderRadius: 14, overflow: "hidden",
      transition: "border-color 0.2s",
    }}>
      <style>{`@keyframes fadeIn { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:translateY(0); } }`}</style>

      {/* ── Header ──────────────────────────────────────────────── */}
      <button type="button" onClick={() => setOpen(v => !v)} style={{
        width: "100%", background: "none", border: "none", cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 18px", gap: 12, fontFamily: "inherit",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: C.dim }}>
            Stale Issues
          </span>
          <div style={{ display: "flex", gap: 5 }}>
            {stale.length > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 5, background: C.amberBg, border: `1px solid ${C.amberBorder}` }}>
                <span style={{ width: 4, height: 4, borderRadius: "50%", background: C.amber, display: "block" }} />
                <span style={{ fontSize: "0.67rem", fontWeight: 700, color: C.amber }}>{stale.length} aging</span>
              </div>
            )}
            {blocked.length > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 5, background: C.redBg, border: `1px solid ${C.redBorder}` }}>
                <span style={{ fontSize: "0.67rem", fontWeight: 700, color: C.red }}>{blocked.length} blocked</span>
              </div>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: "0.7rem", color: C.dim }}>{items.length} tasks</span>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
            style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.2s", flexShrink: 0 }}>
            <path d="M3 5l4 4 4-4" stroke={C.muted} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </button>

      {/* ── Expanded list ────────────────────────────────────────── */}
      {open && (
        <div style={{ borderTop: `1px solid ${C.border}`, animation: "fadeIn 0.2s ease" }}>
          {/* Legend */}
          <div style={{ padding: "7px 18px", borderBottom: "1px solid rgba(255,255,255,0.04)", display: "flex", alignItems: "center", gap: 14 }}>
            {[["≥14d", C.red, "critical"], ["≥7d", C.amber, "aging"], ["<7d", C.muted, "ok"]].map(([label, color, name]) => (
              <div key={name} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: color }} />
                <span style={{ fontSize: "0.65rem", color: C.dim }}>{label} {name}</span>
              </div>
            ))}
          </div>

          {sorted.length === 0 && (
            <div style={{ padding: "18px", textAlign: "center", fontSize: "0.8rem", color: C.dim }}>
              No in-progress issues
            </div>
          )}

          {/* Rows */}
          {sorted.map((item, i) => (
            <div key={item.key + i} style={{
              display: "flex", alignItems: "flex-start", gap: 12,
              padding: "10px 18px",
              borderBottom: i < sorted.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
              background: item.daysInProgress >= 14 ? "rgba(239,68,68,0.025)"
                        : item.daysInProgress >= 7  ? "rgba(245,158,11,0.025)"
                        : "transparent",
            }}>
              {/* Age pill */}
              <div style={{
                flexShrink: 0, minWidth: 40,
                padding: "3px 8px", borderRadius: 6, textAlign: "center", marginTop: 2,
                background: agingBg(item.daysInProgress),
                border: `1px solid ${agingBorder(item.daysInProgress)}`,
              }}>
                <span style={{ fontSize: "0.72rem", fontWeight: 700, color: agingColor(item.daysInProgress), fontFamily: "'IBM Plex Mono', monospace" }}>
                  {item.daysInProgress}d
                </span>
              </div>

              {/* Key + title + blocker */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                  <span style={{ fontSize: "0.67rem", color: C.blue, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600, flexShrink: 0 }}>
                    {item.key}
                  </span>
                  <span style={{ fontSize: "0.65rem", padding: "1px 6px", borderRadius: 4, background: "rgba(255,255,255,0.05)", color: C.dim, flexShrink: 0 }}>
                    {item.status}
                  </span>
                </div>
                <div style={{ fontSize: "0.8rem", color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: item.blockedReason ? 4 : 0 }}>
                  {item.title || "—"}
                </div>
                {item.blockedReason && (
                  <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 3 }}>
                    <div style={{ width: 14, height: 14, borderRadius: 3, background: C.redBg, border: `1px solid ${C.redBorder}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <svg width="6" height="6" viewBox="0 0 6 6" fill="none">
                        <path d="M3 1v2.5M3 4.5v.5" stroke={C.red} strokeWidth="1.2" strokeLinecap="round"/>
                      </svg>
                    </div>
                    <span style={{ fontSize: "0.7rem", color: "rgba(239,68,68,0.7)", fontStyle: "italic" }}>
                      {item.blockedReason}
                    </span>
                  </div>
                )}
              </div>

              {/* Assignee avatar */}
              {item.assignee && (
                <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 5, marginTop: 2 }}>
                  <div style={{ width: 22, height: 22, borderRadius: "50%", background: "rgba(79,124,255,0.12)", border: "1px solid rgba(79,124,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.58rem", fontWeight: 700, color: C.blue }}>
                    {initials(item.assignee)}
                  </div>
                  <span style={{ fontSize: "0.7rem", color: C.muted }}>
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
