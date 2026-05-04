import { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/Sidebar";
import KpiCard from "./components/KpiCard";
import AIPanel from "./components/AIPanel";
import StaleIssuesPanel from "./components/StaleIssuesPanel";
import { useCredentials } from "./hooks/useCredentials";
import { useProjects } from "./hooks/useProjects";
import { fetchLatest, fetchHistory, postSync } from "./api";
import { DEMO_HISTORY, DEMO_ANALYSIS } from "./demo";

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

function buildKpis(snaps, rich) {
  if (!snaps || snaps.length === 0) return null;
  const last = snaps[snaps.length - 1];
  const prev = snaps.length > 1 ? snaps[snaps.length - 2] : null;

  const delta = (cur, pre, lowerBetter) => {
    if (pre == null || pre === 0 || cur == null) return null;
    const pct = ((cur - pre) / pre) * 100;
    const better = lowerBetter ? pct < 0 : pct > 0;
    const sign = pct > 0 ? "+" : "";
    return { text: `${sign}${round1(pct)}%`, good: better };
  };

  const hist = (field) => snaps.map(s => s[field]).filter(v => v != null);

  // ── Reopened Rate % ────────────────────────────────────────────────────────
  const rate     = (last.completedCount ?? 0) > 0 ? (last.reopened / last.completedCount) * 100 : 0;
  const prevRate = prev && (prev.completedCount ?? 0) > 0 ? (prev.reopened / prev.completedCount) * 100 : null;
  const rateHistory = snaps.map(s =>
    (s.completedCount ?? 0) > 0 ? (s.reopened / s.completedCount) * 100 : 0
  );
  const rateDelta = prevRate != null ? (() => {
    const diff = rate - prevRate;
    if (Math.abs(diff) < 0.05) return null;
    return { text: (diff > 0 ? "↑" : "↓") + round1(Math.abs(diff)) + "%", good: diff < 0 };
  })() : null;

  return [
    {
      label: "Cycle Time",
      sublabel: "In Progress → Done",
      value: round1(last.cycleTime ?? 0),
      unit: "d",
      p85: last.cycleTimeP85 != null ? `${round1(last.cycleTimeP85)}d` : null,
      delta: delta(last.cycleTime, prev?.cycleTime, true),
      status: last.cycleTime == null ? "neutral" : last.cycleTime <= 3 ? "good" : last.cycleTime <= 7 ? "warn" : "bad",
      history: hist("cycleTime"),
      lowerBetter: true,
      barMax: 14,
      tooltip: "Median calendar days from 'In Progress' to 'Done'",
    },
    {
      label: "Time to Market",
      sublabel: "Created → Done",
      value: round1(last.timeToMarket ?? 0),
      unit: "d",
      p85: last.timeToMarketP85 != null ? `${round1(last.timeToMarketP85)}d` : null,
      delta: delta(last.timeToMarket, prev?.timeToMarket, true),
      status: last.timeToMarket == null ? "neutral" : last.timeToMarket <= 7 ? "good" : last.timeToMarket <= 14 ? "warn" : "bad",
      history: hist("timeToMarket"),
      lowerBetter: true,
      barMax: 28,
      tooltip: "Median days from ticket creation to completion",
    },
    {
      label: "Flow Efficiency",
      sublabel: "Active / Total time",
      value: round1(last.flowEfficiency ?? 0),
      unit: "%",
      delta: delta(last.flowEfficiency, prev?.flowEfficiency, false),
      status: last.flowEfficiency == null ? "neutral" : last.flowEfficiency >= 40 ? "good" : last.flowEfficiency >= 20 ? "warn" : "bad",
      history: hist("flowEfficiency"),
      lowerBetter: false,
      barMax: 100,
      tooltip: "% of total lead time the item was actively worked on",
    },
    {
      label: "Reopened Rate",
      sublabel: `${last.reopened ?? 0} of ${last.completedCount ?? 0} completed`,
      value: round1(rate),
      unit: "%",
      delta: rateDelta,
      status: rate === 0 ? "good" : rate < 5 ? "warn" : "bad",
      history: rateHistory,
      lowerBetter: true,
      barMax: 20,
      tooltip: "% of completed issues that were reopened at least once",
    },
    {
      label: "WIP",
      sublabel: "In Progress now",
      value: last.wip ?? 0,
      unit: null,
      delta: delta(last.wip, prev?.wip, true),
      status: last.wip == null ? "neutral" : last.wip <= 10 ? "good" : last.wip <= 20 ? "warn" : "bad",
      history: hist("wip"),
      lowerBetter: true,
      barMax: 30,
      tooltip: "Number of issues currently In Progress",
    },
    {
      label: "Backlog Aging",
      sublabel: "Avg days untouched",
      value: round1(last.backlogAging ?? 0),
      unit: "d",
      delta: delta(last.backlogAging, prev?.backlogAging, true),
      status: last.backlogAging == null ? "neutral" : last.backlogAging <= 14 ? "good" : last.backlogAging <= 30 ? "warn" : "bad",
      history: hist("backlogAging"),
      lowerBetter: true,
      barMax: 60,
      tooltip: "Average days since backlog issues were last updated",
    },
  ].map(k => ({ ...k, rich }));
}

/* ─── UpdatedAgo ──────────────────────────────────────────────────────────── */

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

function UpdatedAgo({ timestamp }) {
  const level     = staleLevel(timestamp);
  const ago       = formatAgo(timestamp);
  if (!ago) return null;
  const staleColor = {
    ok:    "rgba(255,255,255,0.35)",
    amber: "#fbbf24",
    red:   "#f87171",
    none:  "rgba(255,255,255,0.18)",
  }[level];
  return (
    <span style={{ fontSize: "0.7rem", color: staleColor, fontFamily: "'IBM Plex Mono', monospace", display: "flex", alignItems: "center", gap: 5, transition: "color 0.3s" }}>
      {level !== "ok" && (
        <span style={{ width: 5, height: 5, borderRadius: "50%", background: staleColor, display: "inline-block", flexShrink: 0 }} />
      )}
      Updated {ago}
    </span>
  );
}

/* ─── StaleBanner ─────────────────────────────────────────────────────────── */

function StaleBanner({ timestamp, onSync }) {
  const level = staleLevel(timestamp);
  if (level === "ok" || level === "none") return null;
  const ago = formatAgo(timestamp);
  const cfg = level === "red"
    ? { bg: "rgba(248,113,113,0.07)", border: "rgba(248,113,113,0.18)", color: "#f87171", icon: "!", text: `Data is ${ago} old — metrics may be stale` }
    : { bg: "rgba(251,191,36,0.07)",  border: "rgba(251,191,36,0.18)",  color: "#fbbf24", icon: "⚠", text: `Data is ${ago} old — consider syncing` };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 14px", borderRadius: 10, background: cfg.bg, border: `1px solid ${cfg.border}` }}>
      <div style={{ width: 20, height: 20, borderRadius: 5, background: cfg.bg, border: `1px solid ${cfg.border}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.7rem", color: cfg.color, fontWeight: 700, flexShrink: 0 }}>
        {cfg.icon}
      </div>
      <span style={{ fontSize: "0.8rem", color: cfg.color, flex: 1 }}>{cfg.text}</span>
      <button type="button" onClick={onSync} style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, borderRadius: 6, color: cfg.color, fontSize: "0.75rem", fontWeight: 600, cursor: "pointer", padding: "3px 10px", fontFamily: "inherit" }}>
        Sync now
      </button>
    </div>
  );
}

/* ─── TweaksPanel ─────────────────────────────────────────────────────────── */

function TweaksPanel({ tweaks, setTweaks, onClose }) {
  const row = (label, children) => (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
      <span style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.5)" }}>{label}</span>
      <div style={{ display: "flex", gap: 4 }}>{children}</div>
    </div>
  );
  const btn = (active, label, onClick) => (
    <button onClick={onClick} style={{
      padding: "4px 10px",
      border: "1px solid " + (active ? "rgba(107,140,255,0.40)" : "rgba(255,255,255,0.1)"),
      borderRadius: 6,
      background: active ? "rgba(107,140,255,0.08)" : "transparent",
      color: active ? "#6b8cff" : "rgba(255,255,255,0.4)",
      fontSize: "0.73rem", cursor: "pointer",
    }}>{label}</button>
  );
  return (
    <div style={{ position: "absolute", top: 44, right: 12, zIndex: 100, background: "#1a1d24", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: "14px 16px", minWidth: 240, display: "flex", flexDirection: "column", gap: 12, boxShadow: "0 8px 32px rgba(0,0,0,0.45)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)" }}>Display</span>
        <button onClick={onClose} style={{ border: "none", background: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: "0.9rem" }}>✕</button>
      </div>
      {row("Cards",      [btn(tweaks.kpiStyle === "rich",        "Rich",         () => setTweaks(t => ({ ...t, kpiStyle: "rich" }))),        btn(tweaks.kpiStyle === "minimal",     "Minimal",     () => setTweaks(t => ({ ...t, kpiStyle: "minimal" })))])}
      {row("Density",    [btn(tweaks.density  === "comfortable", "Comfortable",  () => setTweaks(t => ({ ...t, density: "comfortable" }))),   btn(tweaks.density  === "compact",     "Compact",     () => setTweaks(t => ({ ...t, density: "compact" })))])}
      {row("AI Position",[btn(tweaks.aiTop,                     "Top",          () => setTweaks(t => ({ ...t, aiTop: true }))),               btn(!tweaks.aiTop,                     "Bottom",      () => setTweaks(t => ({ ...t, aiTop: false })))])}
    </div>
  );
}

/* ─── StatusPill ──────────────────────────────────────────────────────────── */

function StatusPill({ state }) {
  const cfg = {
    idle:    { color: "rgba(255,255,255,0.25)", bg: "rgba(255,255,255,0.04)", label: "Idle" },
    syncing: { color: "#fbbf24",               bg: "rgba(251,191,36,0.07)",  label: "Syncing…" },
    done:    { color: "#4ade80",               bg: "rgba(74,222,128,0.07)",  label: "Up to date" },
    error:   { color: "#f87171",               bg: "rgba(248,113,113,0.07)", label: "Error" },
    demo:    { color: "#a78bfa",               bg: "rgba(167,139,250,0.07)", label: "Demo" },
  }[state] ?? { color: "rgba(255,255,255,0.25)", bg: "transparent", label: state };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "3px 10px", borderRadius: 20, background: cfg.bg, border: `1px solid ${cfg.color}40` }}>
      {state === "syncing"
        ? <div style={{ width: 6, height: 6, borderRadius: "50%", border: `1.5px solid ${cfg.color}`, borderTopColor: "transparent", animation: "spin 0.7s linear infinite" }} />
        : <div style={{ width: 6, height: 6, borderRadius: "50%", background: cfg.color }} />}
      <span style={{ fontSize: "0.7rem", fontWeight: 600, color: cfg.color }}>{cfg.label}</span>
    </div>
  );
}

/* ─── App ──────────────────────────────────────────────────────────────────── */

export default function App() {
  const creds = useCredentials();
  const { projects, activeId, setActiveId, active, addProject, removeProject } = useProjects();

  const [snapshots,   setSnapshots]   = useState([]);
  const [analysis,    setAnalysis]    = useState(null);
  const [syncState,   setSyncState]   = useState("idle");
  const [syncError,   setSyncError]   = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tweaksOpen,  setTweaksOpen]  = useState(false);
  const [newLabel,    setNewLabel]    = useState("");
  const [tweaks,      setTweaks]      = useState({ kpiStyle: "rich", density: "comfortable", aiTop: false });

  const pollRef        = useRef(null);
  const activeKey      = active?.label || null;
  const latestSnapshot = snapshots.at(-1) || null;
  const wipItems       = latestSnapshot?.wipItems || [];

  const resetBoard = useCallback(() => {
    setSnapshots([]); setAnalysis(null); setSyncState("idle"); setSyncError(null);
  }, []);

  /* load data when active project changes */
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

  /* sync — source-aware */
  const handleSync = useCallback(async () => {
    if (!active || !creds.connected) return;
    const previousTimestamp = snapshots.at(-1)?.timestamp || null;
    clearTimeout(pollRef.current);
    setSyncState("syncing"); setSyncError(null);
    try {
      await postSync({
        project: active.label,
        source:  creds.source,
        creds:   creds.currentCreds,
        jql:     active.jql,
      });
      let attempts = 0;
      const poll = async () => {
        try {
          const [history, latest] = await Promise.all([fetchHistory(active.label), fetchLatest(active.label)]);
          const merged = mergeHistoryWithLatest(history, latest);
          const latestTs = latest?.timestamp || merged.at(-1)?.timestamp || null;
          if (latestTs && latestTs !== previousTimestamp) {
            setSnapshots(merged);
            setAnalysis(latest?.analysis || null);
            setSyncState("done");
            return;
          }
        } catch {}
        if (++attempts < POLL_MAX_ATTEMPTS) { pollRef.current = setTimeout(poll, POLL_INTERVAL_MS); }
        else { setSyncState("error"); setSyncError("Sync did not produce a new snapshot"); }
      };
      poll();
    } catch (e) {
      setSyncState("error"); setSyncError(e.message);
    }
  }, [active, creds, snapshots]);

  useEffect(() => () => clearTimeout(pollRef.current), []);

  /* demo */
  const handleDemo = useCallback(() => {
    setSnapshots(DEMO_HISTORY);
    setAnalysis(DEMO_ANALYSIS);
    setSyncState("demo");
  }, []);

  /* add project */
  const handleAddProject = useCallback(() => {
    const label = newLabel.trim();
    if (!label) return;
    const jql = `project = "${label.toUpperCase().replace(/\s+/g, "-")}" ORDER BY updated DESC`;
    resetBoard();
    addProject(label, jql);
    setNewLabel("");
  }, [newLabel, addProject, resetBoard]);

  const rich    = tweaks.kpiStyle === "rich";
  const compact = tweaks.density  === "compact";
  const kpis    = buildKpis(snapshots, rich);
  const hasData = kpis != null;
  const gap     = compact ? 14 : 20;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#111318", color: "#dde1ea", fontFamily: "'Inter', system-ui, sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #111318; }
        @keyframes spin { to { transform: rotate(360deg); } }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
      `}</style>

      {sidebarOpen && <Sidebar creds={creds} onDemo={handleDemo} />}

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* ── App bar ──────────────────────────────────────────── */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 14px", height: 48, borderBottom: "1px solid rgba(255,255,255,0.06)", flexShrink: 0, position: "relative" }}>
          {/* Hamburger */}
          <button aria-label={sidebarOpen ? "Hide sidebar" : "Show sidebar"} onClick={() => setSidebarOpen(v => !v)}
            style={{ width: 30, height: 30, border: "1px solid rgba(255,255,255,0.08)", borderRadius: 7, background: "transparent", color: "rgba(255,255,255,0.45)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect y="2" width="14" height="1.5" rx="1" fill="currentColor"/><rect y="6.25" width="14" height="1.5" rx="1" fill="currentColor"/><rect y="10.5" width="14" height="1.5" rx="1" fill="currentColor"/></svg>
          </button>

          <span style={{ fontSize: "0.88rem", fontWeight: 800, letterSpacing: "-0.02em", color: "#fff", whiteSpace: "nowrap" }}>
            AI <span style={{ color: "#6b8cff" }}>Delivery</span> Analyst
          </span>

          {/* Project tabs */}
          <div style={{ display: "flex", alignItems: "center", gap: 2, flex: 1, overflow: "hidden", marginLeft: 6 }}>
            {projects.map(p => (
              <button key={p.id} onClick={() => { resetBoard(); setActiveId(p.id); }} style={{
                padding: "4px 10px", border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.76rem", fontWeight: 600, whiteSpace: "nowrap",
                background: p.id === activeId ? "rgba(107,140,255,0.08)" : "transparent",
                color: p.id === activeId ? "#6b8cff" : "rgba(255,255,255,0.4)",
              }}>
                {p.label}
                {p.id === activeId && (
                  <span onClick={e => { e.stopPropagation(); resetBoard(); removeProject(p.id); }} style={{ marginLeft: 5, opacity: 0.4, fontSize: "0.7rem" }}>✕</span>
                )}
              </button>
            ))}
            <div style={{ display: "flex", gap: 4, marginLeft: 4 }}>
              <input value={newLabel} onChange={e => setNewLabel(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddProject()}
                placeholder="Add project…" style={{ height: 26, borderRadius: 6, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.04)", color: "#dde1ea", padding: "0 8px", fontSize: "0.73rem", outline: "none", width: 110, fontFamily: "inherit" }} />
              <button onClick={handleAddProject} style={{ height: 26, padding: "0 10px", border: "1px solid rgba(107,140,255,0.30)", borderRadius: 6, background: "rgba(107,140,255,0.08)", color: "#6b8cff", fontSize: "0.73rem", cursor: "pointer" }}>+</button>
            </div>
          </div>

          {/* Right side */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
            <StatusPill state={syncState} />
            <UpdatedAgo timestamp={latestSnapshot?.timestamp} />
            {syncError && <span style={{ fontSize: "0.7rem", color: "#f87171", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{syncError}</span>}
            <button onClick={handleSync} disabled={!active || !creds.connected || syncState === "syncing"}
              style={{ height: 28, padding: "0 14px", border: "1px solid rgba(107,140,255,0.30)", borderRadius: 7, background: "rgba(107,140,255,0.08)", color: "#6b8cff", fontSize: "0.76rem", fontWeight: 600, cursor: "pointer", opacity: (!active || !creds.connected) ? 0.4 : 1, transition: "opacity 0.15s" }}>
              ↻ Sync
            </button>
            <button onClick={() => setTweaksOpen(v => !v)} style={{ width: 28, height: 28, border: "1px solid rgba(255,255,255,0.08)", borderRadius: 7, background: tweaksOpen ? "rgba(255,255,255,0.06)" : "transparent", color: "rgba(255,255,255,0.4)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><circle cx="6.5" cy="6.5" r="2" stroke="currentColor" strokeWidth="1.3"/><path d="M6.5 1v1.5M6.5 10.5V12M1 6.5h1.5M10.5 6.5H12M2.4 2.4l1.06 1.06M9.54 9.54l1.06 1.06M9.54 3.46L8.48 4.52M3.46 9.54l-1.06 1.06" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
            </button>
          </div>

          {tweaksOpen && <TweaksPanel tweaks={tweaks} setTweaks={setTweaks} onClose={() => setTweaksOpen(false)} />}
        </div>

        {/* ── Body ────────────────────────────────────────────── */}
        <div style={{ flex: 1, overflow: "auto", padding: compact ? "14px 16px" : "20px 22px", display: "flex", flexDirection: "column", gap }}>

          {/* Empty state */}
          {!active && !hasData && (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>📊</div>
                <p style={{ fontSize: "0.95rem", color: "rgba(255,255,255,0.4)", marginBottom: 6 }}>No project selected</p>
                <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.22)" }}>Add a project above, or load demo data from the sidebar.</p>
              </div>
            </div>
          )}

          {/* Stale data banner */}
          {hasData && syncState !== "demo" && (
            <StaleBanner timestamp={latestSnapshot?.timestamp} onSync={handleSync} />
          )}

          {/* AI panel top */}
          {(active || hasData) && tweaks.aiTop && (
            <AIPanel analysis={analysis} prominent={!!analysis} />
          )}

          {/* KPI grid */}
          {(active || hasData) && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0,1fr))", gap: compact ? 10 : 14 }}>
              {(hasData ? kpis : Array(6).fill(null)).map((kpi, i) => (
                kpi
                  ? <KpiCard key={kpi.label} {...kpi} compact={compact} />
                  : <div key={i} style={{ borderRadius: 12, background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.05)", padding: compact ? "12px 14px" : "16px 18px", minHeight: 100, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.15)" }}>—</span>
                    </div>
              ))}
            </div>
          )}

          {/* Stale Issues Panel */}
          {(active || hasData) && wipItems.length > 0 && (
            <StaleIssuesPanel items={wipItems} threshold={5} />
          )}

          {/* AI panel bottom */}
          {(active || hasData) && !tweaks.aiTop && (
            <AIPanel analysis={analysis} prominent={!!analysis} />
          )}

          {/* No data hint */}
          {active && !hasData && syncState === "idle" && (
            <div style={{ padding: "12px 16px", borderRadius: 10, background: "rgba(107,140,255,0.04)", border: "1px solid rgba(107,140,255,0.10)", fontSize: "0.8rem", color: "rgba(255,255,255,0.35)", lineHeight: 1.6 }}>
              Open the sidebar, connect a source and click <strong style={{ color: "rgba(255,255,255,0.55)" }}>↻ Sync</strong> — or load demo data.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
