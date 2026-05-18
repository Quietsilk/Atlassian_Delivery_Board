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

function issueHref(item, issueBaseUrl) {
  if (item.url) return item.url;
  if (issueBaseUrl && /^[A-Z][A-Z0-9]+-\d+$/.test(item.key || "")) {
    return `${issueBaseUrl.replace(/\/$/, "")}/browse/${item.key}`;
  }
  return null;
}

export default function StaleIssuesPanel({ items = [], threshold = 5, issueBaseUrl = null }) {
  const T = useT();

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
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "13px 16px", gap: 12, fontFamily: "inherit",
        background: T.bgCard,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: font.size.sm, fontWeight: 700, letterSpacing: font.tracking.normal, color: T.text }}>
            Stale Issues
          </span>
          <div style={{ display: "flex", gap: 5 }}>
            {stale.length > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: radius.sm, background: T.warnBg, border: `1px solid ${T.warnBdr}` }}>
                <span style={{ width: 4, height: 4, borderRadius: "50%", background: T.warn, display: "block" }} />
                <span style={{ fontSize: font.size.xs, fontWeight: 700, color: T.warn }}>{stale.length} aging</span>
              </div>
            )}
            {blocked.length > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: radius.sm, background: T.badBg, border: `1px solid ${T.badBdr}` }}>
                <span style={{ fontSize: font.size.xs, fontWeight: 700, color: T.bad }}>{blocked.length} blocked</span>
              </div>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: "0.7rem", color: T.textFaint }}>{items.length} tasks</span>
        </div>
      </div>

      {/* ── List ─────────────────────────────────────────────────── */}
      <div style={{ borderTop: `1px solid ${T.border}`, animation: `fadeIn ${transition.normal} ease` }}>
          {/* Legend */}
          <div style={{ padding: "8px 16px", borderBottom: `1px solid ${T.borderSub}`, display: "flex", alignItems: "center", gap: 14, background: T.bgCardHov }}>
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
          <div style={{ maxHeight: "min(42vh, 420px)", overflowY: "auto", overscrollBehavior: "contain" }}>
            {sorted.map((item, i) => {
              const href = issueHref(item, issueBaseUrl);
              const RowTag = href ? "a" : "div";
              return (
              <RowTag key={item.key + i} href={href || undefined} target={href ? "_blank" : undefined} rel={href ? "noreferrer" : undefined} style={{
                display: "flex", alignItems: "flex-start", gap: 12,
                padding: "10px 16px",
                borderBottom: i < sorted.length - 1 ? `1px solid ${T.borderSub}` : "none",
                color: "inherit", textDecoration: "none",
                cursor: href ? "pointer" : "default",
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
                    <span style={{ fontSize: "0.65rem", padding: "1px 6px", borderRadius: radius.sm, background: T.borderSub, color: T.textFaint, flexShrink: 0 }}>
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
              </RowTag>
              );
            })}
          </div>
      </div>
    </div>
  );
}
