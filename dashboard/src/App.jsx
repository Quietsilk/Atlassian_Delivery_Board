import { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/Sidebar";
import KpiCard from "./components/KpiCard";
import AIPanel from "./components/AIPanel";
import StaleIssuesPanel from "./components/StaleIssuesPanel";

import { useCredentials } from "./hooks/useCredentials";
import { useProjects } from "./hooks/useProjects";
import { useTheme } from "./hooks/useTheme";
import { ThemeContext } from "./context/ThemeContext";
import { fetchLatest, fetchHistory, postSync } from "./api";
import { DEMO_HISTORY, DEMO_ANALYSIS } from "./demo";
import { font, radius, transition } from "./tokens";

/* ─── constants ───────────────────────────────────────────────────────────── */

const POLL_MAX_ATTEMPTS = 20;
const POLL_INTERVAL_MS  = 3000;

/* ─── helpers ─────────────────────────────────────────────────────────────── */

function round1(n) { return Math.round(n * 10) / 10; }

function mergeHistoryWithLatest(history, latest) {
  const result = [...(history || [])];
  if (!latest) return result;
  const lastIndex = result.findIndex(s => s.timestamp === latest.timestamp);
  if (lastIndex >= 0) result[lastIndex] = latest;
  else result.push(latest);
  return result;
}

/* delta helpers */

function deltaFlow(cur, pre, unit, throughput) {
  if (pre == null || pre === 0 || cur == null || throughput < 5) return null;
  const diff = cur - pre;
  if (Math.abs(diff) < 0.1) return null;
  const sign = diff > 0 ? "+" : "";
  return { text: `${sign}${round1(diff)}${unit} vs last`, good: diff < 0 };
}

function deltaSnap(cur, pre, lowerBetter) {
  if (pre == null || pre === 0 || cur == null) return null;
  const diff = cur - pre;
  if (Math.abs(diff) < 0.05) return null;
  const pct = (diff / Math.abs(pre)) * 100;
  if (Math.abs(pct) > 200) return null;
  const sign = diff > 0 ? "+" : "";
  const pSign = pct > 0 ? "+" : "";
  return { text: `${sign}${round1(diff)} (${pSign}${round1(pct)}%)`, good: lowerBetter ? diff < 0 : diff > 0 };
}

function deltaPct(cur, pre, lowerBetter) {
  if (pre == null || cur == null) return null;
  const diff = cur - pre;
  if (Math.abs(diff) < 0.5) return null;
  const sign = diff > 0 ? "+" : "";
  return { text: `${sign}${round1(diff)}% vs last`, good: lowerBetter ? diff < 0 : diff > 0 };
}

/* insight helpers */

function buildInsight(key, last, wipItems) {
  const wip          = last.wip ?? 0;
  const backlogAging = last.backlogAging ?? 0;
  const flowEff      = last.flowEfficiency ?? 0;
  const reopened     = last.reopened ?? 0;
  const items        = wipItems || [];

  switch (key) {
    case "cycleTime": {
      const long = items.filter(i => i.daysInProgress >= 14);
      if (long.length > 0) return { text: `${long.length} item${long.length > 1 ? "s" : ""} >14d in progress`, level: "bad" };
      if (wip > 7)         return { text: `High WIP: ${wip}`, level: "warn" };
      return { text: "Stable flow", level: "neutral" };
    }
    case "timeToMarket": {
      if (backlogAging > 20) return { text: `Old backlog: ${round1(backlogAging)}d avg`, level: "warn" };
      return { text: "Normal lead time", level: "neutral" };
    }
    case "flowEfficiency": {
      if (flowEff < 20) return { text: "Too much waiting", level: "bad" };
      if (flowEff < 40) return { text: "Moderate delays", level: "warn" };
      return { text: "Healthy flow", level: "neutral" };
    }
    case "wip": {
      const byAssignee = {};
      for (const i of items) {
        if (i.assignee) byAssignee[i.assignee] = (byAssignee[i.assignee] || 0) + 1;
      }
      const overloaded = Object.entries(byAssignee).find(([, cnt]) => cnt > 4);
      if (overloaded) return { text: `${overloaded[0]} overloaded (${overloaded[1]})`, level: "warn" };
      if (wip > 7)    return { text: "Too many parallel tasks", level: "warn" };
      return { text: "WIP under control", level: "neutral" };
    }
    case "backlogAging": {
      if (backlogAging > 30) return { text: `Backlog too old (${round1(backlogAging)}d)`, level: "bad" };
      if (backlogAging > 14) return { text: "Aging increasing", level: "warn" };
      return { text: "Backlog healthy", level: "neutral" };
    }
    case "reopened": {
      if (reopened > 0) return { text: `${reopened} reopened issue${reopened > 1 ? "s" : ""}`, level: "warn" };
      return { text: "No reopens", level: "neutral" };
    }
    default: return null;
  }
}

function buildKpis(snaps, wipItems) {
  if (!snaps || snaps.length === 0) return null;
  const last = snaps[snaps.length - 1];
  const prev = snaps.length > 1 ? snaps[snaps.length - 2] : null;
  const throughput = last.throughput ?? 0;

  const rate     = (last.completedCount ?? 0) > 0 ? (last.reopened / last.completedCount) * 100 : 0;
  const prevRate = prev && (prev.completedCount ?? 0) > 0 ? (prev.reopened / prev.completedCount) * 100 : null;

  return [
    {
      key: "cycleTime",
      label: "Cycle Time", sublabel: "In Progress → Done",
      value: round1(last.cycleTime ?? 0), unit: "d",
      delta: deltaFlow(last.cycleTime, prev?.cycleTime, "d", throughput),
      insight: buildInsight("cycleTime", last, wipItems),
      status: last.cycleTime == null ? "neutral" : last.cycleTime <= 3 ? "good" : last.cycleTime <= 7 ? "warn" : "bad",
      barMax: 14, tooltip: "Median calendar days from 'In Progress' to 'Done'",
    },
    {
      key: "timeToMarket",
      label: "Time to Market", sublabel: "Created → Done",
      value: round1(last.timeToMarket ?? 0), unit: "d",
      delta: deltaFlow(last.timeToMarket, prev?.timeToMarket, "d", throughput),
      insight: buildInsight("timeToMarket", last, wipItems),
      status: last.timeToMarket == null ? "neutral" : last.timeToMarket <= 7 ? "good" : last.timeToMarket <= 14 ? "warn" : "bad",
      barMax: 28, tooltip: "Median days from ticket creation to completion",
    },
    {
      key: "flowEfficiency",
      label: "Flow Efficiency", sublabel: "Active / Total time",
      value: round1(last.flowEfficiency ?? 0), unit: "%",
      delta: deltaPct(last.flowEfficiency, prev?.flowEfficiency, false),
      insight: buildInsight("flowEfficiency", last, wipItems),
      status: last.flowEfficiency == null ? "neutral" : last.flowEfficiency >= 40 ? "good" : last.flowEfficiency >= 20 ? "warn" : "bad",
      barMax: 100, tooltip: "% of total lead time the item was actively worked on",
    },
    {
      key: "reopened",
      label: "Reopened Rate", sublabel: `${last.reopened ?? 0} of ${last.completedCount ?? 0} completed`,
      value: round1(rate), unit: "%",
      delta: deltaPct(rate, prevRate, true),
      insight: buildInsight("reopened", last, wipItems),
      status: rate === 0 ? "good" : rate < 5 ? "warn" : "bad",
      barMax: 20, tooltip: "% of completed issues that were reopened at least once",
    },
    {
      key: "wip",
      label: "WIP", sublabel: "In Progress now",
      value: last.wip ?? 0, unit: null,
      delta: deltaSnap(last.wip, prev?.wip, true),
      insight: buildInsight("wip", last, wipItems),
      status: last.wip == null ? "neutral" : last.wip <= 10 ? "good" : last.wip <= 20 ? "warn" : "bad",
      barMax: 30, tooltip: "Number of issues currently In Progress",
    },
    {
      key: "backlogAging",
      label: "Backlog Aging", sublabel: "Avg days untouched",
      value: round1(last.backlogAging ?? 0), unit: "d",
      delta: deltaSnap(last.backlogAging, prev?.backlogAging, true),
      insight: buildInsight("backlogAging", last, wipItems),
      status: last.backlogAging == null ? "neutral" : last.backlogAging <= 14 ? "good" : last.backlogAging <= 30 ? "warn" : "bad",
      barMax: 60, tooltip: "Average days since backlog issues were last updated",
    },
  ];
}

/* ─── Staleness helpers ───────────────────────────────────────────────────── */

function staleLevel(isoTs) {
  if (!isoTs) return "none";
  const mins = (Date.now() - new Date(isoTs).getTime()) / 60000;
  if (mins > 120) return "red";
  if (mins > 30)  return "amber";
  return "ok";
}

function formatAgo(isoTs) {
  if (!isoTs) return null;
  const mins = Math.floor((Date.now() - new Date(isoTs).getTime()) / 60000);
  if (mins < 1)    return "just now";
  if (mins < 60)   return `${mins}m ago`;
  if (mins < 1440) return `${Math.floor(mins / 60)}h ago`;
  return `${Math.floor(mins / 1440)}d ago`;
}

/* ─── UpdatedAgo ──────────────────────────────────────────────────────────── */

function UpdatedAgo({ timestamp, T }) {
  const level = staleLevel(timestamp);
  const ago   = formatAgo(timestamp);
  if (!ago) return null;
  const staleColor = { ok: T.textSec, amber: T.warn, red: T.bad, none: T.textFaint }[level];
  return (
    <span style={{ fontSize: "0.7rem", color: staleColor, fontFamily: font.family.mono, display: "flex", alignItems: "center", gap: 5, transition: "color 0.3s" }}>
      {level !== "ok" && (
        <span style={{ width: 5, height: 5, borderRadius: "50%", background: staleColor, display: "inline-block", flexShrink: 0 }} />
      )}
      Updated {ago}
    </span>
  );
}

/* ─── StatusPill ──────────────────────────────────────────────────────────── */

function StatusPill({ state, T }) {
  const cfg = {
    idle:    { fg: T.textMuted, bg: T.bgCard,  label: "Idle" },
    syncing: { fg: T.warn,     bg: T.warnBg,  label: "Syncing…" },
    done:    { fg: T.good,     bg: T.goodBg,  label: "Up to date" },
    error:   { fg: T.bad,      bg: T.badBg,   label: "Error" },
    demo:    { fg: T.demo,     bg: T.demoBg,  label: "Demo" },
  }[state] ?? { fg: T.textMuted, bg: "transparent", label: state };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "3px 10px", borderRadius: 20, background: cfg.bg, border: `1px solid ${cfg.fg}40` }}>
      {state === "syncing"
        ? <div style={{ width: 6, height: 6, borderRadius: "50%", border: `1.5px solid ${cfg.fg}`, borderTopColor: "transparent", animation: "spin 0.7s linear infinite" }} />
        : <div style={{ width: 6, height: 6, borderRadius: "50%", background: cfg.fg }} />}
      <span style={{ fontSize: font.size.xs, fontWeight: font.weight.semibold, color: cfg.fg }}>{cfg.label}</span>
    </div>
  );
}

/* ─── ThemeToggle ─────────────────────────────────────────────────────────── */

function ThemeToggle({ mode, onToggle, T }) {
  return (
    <button onClick={onToggle} title="Toggle theme" style={{
      width: 28, height: 28, borderRadius: radius.md,
      border: `1px solid ${T.border}`,
      background: T.bgCard,
      cursor: "pointer",
      display: "flex", alignItems: "center", justifyContent: "center",
      transition: `all ${transition.fast}`, flexShrink: 0,
    }}>
      {mode === "dark" ? (
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <circle cx="7.5" cy="7.5" r="3" stroke={T.textMuted} strokeWidth="1.3"/>
          <path d="M7.5 1v1.5M7.5 12.5V14M1 7.5h1.5M12.5 7.5H14M2.9 2.9l1.1 1.1M11 11l1.1 1.1M11 2.9L9.9 4M4 11l-1.1 1.1" stroke={T.textMuted} strokeWidth="1.3" strokeLinecap="round"/>
        </svg>
      ) : (
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <path d="M12.5 9.5A6 6 0 015.5 2.5a6 6 0 100 10 6 6 0 007-3z" stroke={T.textMuted} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
    </button>
  );
}

/* ─── App ──────────────────────────────────────────────────────────────────── */

export default function App() {
  const { mode, T, toggleTheme } = useTheme();
  const creds = useCredentials();
  const { projects, activeId, setActiveId, active, addProject, removeProject } = useProjects();

  const [snapshots,   setSnapshots]   = useState([]);
  const [analysis,    setAnalysis]    = useState(null);
  const [syncState,   setSyncState]   = useState("idle");
  const [syncError,   setSyncError]   = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [newLabel,    setNewLabel]    = useState("");

  const compact = false;

  const pollRef        = useRef(null);
  const activeKey      = active?.label || null;
  const latestSnapshot = snapshots.at(-1) || null;
  const wipItems       = latestSnapshot?.wipItems || [];

  /* sync body background + data-theme attribute with theme */
  useEffect(() => {
    document.body.style.background = T.bg;
    document.documentElement.dataset.theme = mode;
  }, [T.bg, mode]);

  const resetBoard = useCallback(() => {
    setSnapshots([]); setAnalysis(null); setSyncState("idle"); setSyncError(null);
  }, []);

  useEffect(() => {
    if (!activeKey) return;
    let cancelled = false;
    Promise.all([fetchHistory(activeKey), fetchLatest(activeKey)])
      .then(([history, latest]) => {
        if (cancelled) return;
        const merged = mergeHistoryWithLatest(history, latest);
        setSnapshots(merged);
        setAnalysis(latest?.analysis || null);
        if (merged.length) setSyncState("done");
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [activeKey]);

  const handleSync = useCallback(async () => {
    if (!projects.length || !creds.connected) return;
    const previousTimestamp = snapshots.at(-1)?.timestamp || null;
    clearTimeout(pollRef.current);
    setSyncState("syncing"); setSyncError(null);
    try {
      await Promise.all(projects.map(p =>
        postSync({ project: p.label, source: creds.source, creds: creds.currentCreds, jql: p.jql })
      ));
      if (!active) { setSyncState("done"); return; }
      let attempts = 0;
      const poll = async () => {
        try {
          const [history, latest] = await Promise.all([fetchHistory(active.label), fetchLatest(active.label)]);
          const merged = mergeHistoryWithLatest(history, latest);
          const latestTs = latest?.timestamp || merged.at(-1)?.timestamp || null;
          if (latestTs && latestTs !== previousTimestamp) {
            setSnapshots(merged); setAnalysis(latest?.analysis || null); setSyncState("done"); return;
          }
        } catch {}
        if (++attempts < POLL_MAX_ATTEMPTS) { pollRef.current = setTimeout(poll, POLL_INTERVAL_MS); }
        else { setSyncState("error"); setSyncError("Sync did not produce a new snapshot"); }
      };
      poll();
    } catch (e) { setSyncState("error"); setSyncError(e.message); }
  }, [active, projects, creds, snapshots]);

  useEffect(() => () => clearTimeout(pollRef.current), []);

  const handleDemo = useCallback(() => {
    setSnapshots(DEMO_HISTORY); setAnalysis(DEMO_ANALYSIS); setSyncState("demo");
  }, []);

  const handleAddProject = useCallback(() => {
    const label = newLabel.trim();
    if (!label) return;
    const jql = `project = "${label.toUpperCase().replace(/\s+/g, "-")}" ORDER BY updated DESC`;
    resetBoard(); addProject(label, jql); setNewLabel("");
  }, [newLabel, addProject, resetBoard]);

  const kpis    = buildKpis(snapshots, wipItems);
  const hasData = kpis != null;
  const gap     = compact ? 14 : 20;

  return (
    <ThemeContext.Provider value={T}>
      <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: T.bg, color: T.text, fontFamily: font.family.sans, transition: `background ${transition.normal}, color ${transition.normal}` }}>
        <style>{`
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');
          * { box-sizing: border-box; margin: 0; padding: 0; }
          @keyframes spin { to { transform: rotate(360deg); } }
          [data-theme="dark"]  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); }
          [data-theme="light"] ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); }
          ::-webkit-scrollbar { width: 5px; height: 5px; }
          ::-webkit-scrollbar-track { background: transparent; }
        `}</style>

        {sidebarOpen && <Sidebar creds={creds} onDemo={handleDemo} />}

        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

          {/* ── App bar ────────────────────────────────────────── */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 14px", height: 48, borderBottom: `1px solid ${T.borderSub}`, flexShrink: 0, position: "relative", background: T.bgBar }}>
            {/* Hamburger */}
            <button aria-label={sidebarOpen ? "Hide sidebar" : "Show sidebar"} onClick={() => setSidebarOpen(v => !v)}
              style={{ width: 30, height: 30, border: `1px solid ${T.border}`, borderRadius: radius.md, background: "transparent", color: T.textSec, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect y="2" width="14" height="1.5" rx="1" fill="currentColor"/><rect y="6.25" width="14" height="1.5" rx="1" fill="currentColor"/><rect y="10.5" width="14" height="1.5" rx="1" fill="currentColor"/></svg>
            </button>

            <span style={{ fontSize: font.size.lg, fontWeight: font.weight.extrabold, letterSpacing: font.tracking.tight, color: T.text, whiteSpace: "nowrap" }}>
              AI <span style={{ color: T.brand }}>Delivery</span> Analyst
            </span>

            {/* Project tabs */}
            <div style={{ display: "flex", alignItems: "center", gap: 2, flex: 1, overflow: "hidden", marginLeft: 6 }}>
              {projects.map(p => (
                <button key={p.id} onClick={() => { resetBoard(); setActiveId(p.id); }} style={{
                  padding: "4px 10px", border: "none", borderRadius: radius.sm, cursor: "pointer", fontSize: "0.76rem", fontWeight: 600, whiteSpace: "nowrap",
                  background: p.id === activeId ? T.brandBg : "transparent",
                  color: p.id === activeId ? T.brand : T.textLabel,
                }}>
                  {p.label}
                  {p.id === activeId && (
                    <span onClick={e => { e.stopPropagation(); resetBoard(); removeProject(p.id); }} style={{ marginLeft: 5, opacity: 0.4, fontSize: "0.7rem" }}>✕</span>
                  )}
                </button>
              ))}
              <div style={{ display: "flex", gap: 4, marginLeft: 4 }}>
                <input value={newLabel} onChange={e => setNewLabel(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddProject()}
                  placeholder="Add project…" style={{ height: 26, borderRadius: radius.sm, border: `1px solid ${T.border}`, background: T.bgCard, color: T.text, padding: "0 8px", fontSize: "0.73rem", outline: "none", width: 110, fontFamily: "inherit" }} />
                <button onClick={handleAddProject} style={{ height: 26, padding: "0 10px", border: `1px solid ${T.brandBdr}`, borderRadius: radius.sm, background: T.brandBg, color: T.brand, fontSize: "0.73rem", cursor: "pointer" }}>+</button>
              </div>
            </div>

            {/* Right side */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
              <StatusPill state={syncState} T={T} />
              <UpdatedAgo timestamp={latestSnapshot?.timestamp} T={T} />
              {syncError && <span style={{ fontSize: "0.7rem", color: T.bad, maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{syncError}</span>}
              <button onClick={handleSync} disabled={!projects.length || !creds.connected || syncState === "syncing"}
                style={{ height: 28, padding: "0 14px", border: `1px solid ${T.brandBdr}`, borderRadius: radius.md, background: T.brandBg, color: T.brand, fontSize: "0.76rem", fontWeight: 600, cursor: "pointer", opacity: (!projects.length || !creds.connected) ? 0.4 : 1, transition: `opacity ${transition.fast}` }}>
                ↻ Sync
              </button>
              <ThemeToggle mode={mode} onToggle={toggleTheme} T={T} />
            </div>
          </div>

          {/* ── Body ──────────────────────────────────────────── */}
          <div style={{ flex: 1, overflow: "auto", padding: compact ? "14px 16px" : "20px 22px", display: "flex", flexDirection: "column", gap }}>

            {!active && !hasData && (
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>📊</div>
                  <p style={{ fontSize: "0.95rem", color: T.textLabel, marginBottom: 6 }}>No project selected</p>
                  <p style={{ fontSize: "0.8rem", color: T.textFaint }}>Add a project above, or load demo data from the sidebar.</p>
                </div>
              </div>
            )}

            {(active || hasData) && <AIPanel analysis={analysis} prominent={!!analysis} />}

            {(active || hasData) && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0,1fr))", gap: compact ? 10 : 14 }}>
                {(hasData ? kpis : Array(6).fill(null)).map((kpi, i) => (
                  kpi
                    ? <KpiCard key={kpi.label} {...kpi} compact={compact} />
                    : <div key={i} style={{ borderRadius: radius.card, background: T.bgCard, border: `1px solid ${T.borderSub}`, padding: compact ? "12px 14px" : "16px 18px", minHeight: 100, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <span style={{ fontSize: "0.75rem", color: T.textFaint }}>—</span>
                      </div>
                ))}
              </div>
            )}

            {(active || hasData) && wipItems.length > 0 && (
              <StaleIssuesPanel items={wipItems} threshold={5} />
            )}

            {active && !hasData && syncState === "idle" && (
              <div style={{ padding: "12px 16px", borderRadius: 10, background: T.brandBg, border: `1px solid ${T.brandBdr}`, fontSize: "0.8rem", color: T.textMuted, lineHeight: 1.6 }}>
                Open the sidebar, connect a source and click <strong style={{ color: T.textSec }}>↻ Sync</strong> — or load demo data.
              </div>
            )}
          </div>
        </div>
      </div>
    </ThemeContext.Provider>
  );
}
