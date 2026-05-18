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

function issueHref(item, issueBaseUrl) {
  if (item.url) return item.url;
  if (issueBaseUrl && /^[A-Z][A-Z0-9]+-\d+$/.test(item.key || "")) {
    return `${issueBaseUrl.replace(/\/$/, "")}/browse/${item.key}`;
  }
  return null;
}

function statusRank(status) {
  const normalized = (status || "").toLowerCase();
  if (normalized.includes("selected")) return 0;
  if (normalized.includes("progress")) return 1;
  if (normalized.includes("review")) return 2;
  if (normalized.includes("block")) return 3;
  return 4;
}

export default function StaleIssuesPanel({ items = [], threshold = 5, issueBaseUrl = null }) {
  const T = useT();
  const [filter, setFilter] = useState("all");

  const stale   = items.filter(i => i.daysInProgress >= threshold);
  const blocked = items.filter(i => i.blockedReason);
  const unassigned = items.filter(i => !i.assignee);
  const filtered = items.filter(item => {
    if (filter === "aging") return item.daysInProgress >= threshold;
    if (filter === "blocked") return Boolean(item.blockedReason);
    if (filter === "unassigned") return !item.assignee;
    return true;
  });
  const sorted  = [...filtered].sort((a, b) => {
    const rank = statusRank(a.status) - statusRank(b.status);
    if (rank !== 0) return rank;
    return b.daysInProgress - a.daysInProgress;
  });
  const groups = sorted.reduce((acc, item) => {
    const status = item.status || "Unknown";
    if (!acc[status]) acc[status] = [];
    acc[status].push(item);
    return acc;
  }, {});
  const groupNames = Object.keys(groups).sort((a, b) => {
    const rank = statusRank(a) - statusRank(b);
    if (rank !== 0) return rank;
    return a.localeCompare(b);
  });
  const filters = [
    { key: "all", label: "All", count: items.length },
    { key: "aging", label: "Aging", count: stale.length },
    { key: "blocked", label: "Blocked", count: blocked.length },
    { key: "unassigned", label: "Unassigned", count: unassigned.length },
  ];

  return (
    <div style={{
      background: "transparent",
      overflow: "hidden",
    }}>
      <style>{`@keyframes fadeIn { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:translateY(0); } }`}</style>

      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "6px 0 8px", gap: 12, fontFamily: "inherit",
        background: "transparent",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: font.size.sm, fontWeight: 700, letterSpacing: font.tracking.normal, color: T.text }}>
            In Progress Issues
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
          <span style={{ fontSize: "0.7rem", color: T.textFaint }}>{items.length} issues</span>
        </div>
      </div>

      <div style={{ display: "flex", gap: 4, padding: "0 0 8px", flexWrap: "wrap" }}>
        {filters.map(option => {
          const active = filter === option.key;
          return (
            <button key={option.key} type="button" onClick={() => setFilter(option.key)} style={{
              height: 26,
              padding: "0 8px",
              borderRadius: radius.sm,
              border: `1px solid ${active ? T.brandBdr : "transparent"}`,
              background: active ? T.brandBg : "transparent",
              color: active ? T.brand : T.textSec,
              fontSize: font.size.xs,
              fontWeight: active ? 700 : 600,
              cursor: "pointer",
            }}>
              {option.label} <span style={{ color: active ? T.brand : T.textFaint }}>{option.count}</span>
            </button>
          );
        })}
      </div>

      <div style={{ animation: `fadeIn ${transition.normal} ease` }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: "92px minmax(220px, 1fr) 110px 120px 86px",
            gap: 12,
            padding: "8px 10px",
            borderBottom: `1px solid ${T.borderSub}`,
            borderTop: `1px solid ${T.borderSub}`,
            background: T.bgCardHov,
            color: T.textFaint,
            fontSize: font.size.xxs,
            fontWeight: 700,
            letterSpacing: font.tracking.wide,
            textTransform: "uppercase",
          }}>
            <span>Key</span>
            <span>Summary</span>
            <span>Status</span>
            <span>Assignee</span>
            <span style={{ textAlign: "right" }}>Age</span>
          </div>

          {sorted.length === 0 && (
            <div style={{ padding: "18px 10px", textAlign: "center", fontSize: "0.8rem", color: T.textFaint }}>
              No matching in-progress issues
            </div>
          )}

          <div style={{ maxHeight: "min(42vh, 420px)", overflowY: "auto", overscrollBehavior: "contain" }}>
            {groupNames.map(status => (
              <div key={status}>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "9px 10px 5px",
                  color: T.textMuted,
                  fontSize: font.size.xxs,
                  fontWeight: 700,
                  letterSpacing: font.tracking.wide,
                  textTransform: "uppercase",
                }}>
                  <span>{status}</span>
                  <span style={{ color: T.textFaint }}>{groups[status].length}</span>
                </div>
                {groups[status].map((item, i) => {
                  const href = issueHref(item, issueBaseUrl);
                  const RowTag = href ? "a" : "div";
                  return (
                  <RowTag key={item.key + i} href={href || undefined} target={href ? "_blank" : undefined} rel={href ? "noreferrer" : undefined} style={{
                    display: "grid",
                    gridTemplateColumns: "92px minmax(220px, 1fr) 110px 120px 86px",
                    alignItems: "center",
                    gap: 12,
                    padding: "9px 10px",
                    borderBottom: `1px solid ${T.borderSub}`,
                    color: "inherit", textDecoration: "none",
                    cursor: href ? "pointer" : "default",
                    background: "transparent",
                  }}>
                    <span style={{ fontSize: font.size.xs, color: T.brand, fontFamily: font.family.mono, fontWeight: 700, whiteSpace: "nowrap" }}>
                      {item.key}
                    </span>
                    <div style={{ minWidth: 0 }}>
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
                    <span style={{
                      justifySelf: "start",
                      fontSize: "0.65rem",
                      padding: "2px 7px",
                      borderRadius: radius.sm,
                      background: T.borderSub,
                      color: T.textSec,
                      fontWeight: 700,
                      textTransform: "uppercase",
                      whiteSpace: "nowrap",
                    }}>
                      {item.status}
                    </span>
                    <span style={{ fontSize: font.size.xs, color: T.textMuted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.assignee || "Unassigned"}
                    </span>
                    <span style={{
                      justifySelf: "end",
                      minWidth: 46,
                      padding: "3px 8px",
                      borderRadius: radius.sm,
                      textAlign: "center",
                      background: agingBg(T, item.daysInProgress),
                      border: `1px solid ${agingBorder(T, item.daysInProgress)}`,
                      color: agingColor(T, item.daysInProgress),
                      fontSize: font.size.xs,
                      fontWeight: 700,
                      fontFamily: font.family.mono,
                    }}>
                      {item.daysInProgress}d
                    </span>
                  </RowTag>
                  );
                })}
              </div>
            ))}
          </div>
      </div>
    </div>
  );
}
