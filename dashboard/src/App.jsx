import { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/Sidebar";
import KpiCard from "./components/KpiCard";
import AIPanel from "./components/AIPanel";
import { useCredentials } from "./hooks/useCredentials";
import { useProjects } from "./hooks/useProjects";
import { fetchLatest, fetchHistory, postSync } from "./api";
import { DEMO_HISTORY, DEMO_ANALYSIS } from "./demo";

/* ─── constants ───────────────────────────────────────────────────────────── */

const POLL_MAX_ATTEMPTS = 20;   // max polls before giving up
const POLL_INTERVAL_MS  = 3000; // ms between polls  → total timeout = 60 s

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
      label: "Reopened",
      sublabel: "Reopened issues",
      value: last.reopened ?? 0,
      unit: null,
      delta: delta(last.reopened, prev?.reopened, true),
      status: last.reopened == null ? "neutral" : last.reopened <= 0 ? "good" : last.reopened < 3 ? "warn" : "bad",
      history: hist("reopened"),
      lowerBetter: true,
      barMax: 10,
      tooltip: "Number of completed issues that were reopened at least once",
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

/* ─── inline TweaksPanel ───────────────────────────────────────────────────── */

function TweaksPanel({ tweaks, setTweaks, onClose }) {
  const row = (label, children) => (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
      <span style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.5)" }}>{label}</span>
      <div style={{ display: "flex", gap: 4 }}>{children}</div>
    </div>
  );
  const btn = (active, label, onClick) => (
    <button onClick={onClick} style={{
      padding: "4px 10px", border: "1px solid " + (active ? "rgba(79,124,255,0.5)" : "rgba(255,255,255,0.1)"),
      borderRadius: 6, background: active ? "rgba(79,124,255,0.15)" : "transparent",
      color: active ? "#4f7cff" : "rgba(255,255,255,0.4)", fontSize: "0.73rem", cursor: "pointer",
    }}>{label}</button>
  );

  return (
    <div style={{
      position: "absolute", top: 44, right: 12, zIndex: 100,
      background: "#16181f", border: "1px solid rgba(255,255,255,0.1)",
      borderRadius: 12, padding: "14px 16px", minWidth: 240,
      display: "flex", flexDirection: "column", gap: 12,
      boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)" }}>Display</span>
        <button onClick={onClose} style={{ border: "none", background: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: "0.9rem" }}>✕</button>
      </div>
      {row("Cards", [
        btn(tweaks.kpiStyle === "rich",    "Rich",    () => setTweaks(t => ({ ...t, kpiStyle: "rich" }))),
        btn(tweaks.kpiStyle === "minimal", "Minimal", () => setTweaks(t => ({ ...t, kpiStyle: "minimal" }))),
      ])}
      {row("Density", [
        btn(tweaks.density === "comfortable", "Comfortable", () => setTweaks(t => ({ ...t, density: "comfortable" }))),
        btn(tweaks.density === "compact",     "Compact",     () => setTweaks(t => ({ ...t, density: "compact" }))),
      ])}
      {row("AI Position", [
        btn(tweaks.aiTop,  "Top",    () => setTweaks(t => ({ ...t, aiTop: true }))),
        btn(!tweaks.aiTop, "Bottom", () => setTweaks(t => ({ ...t, aiTop: false }))),
      ])}
    </div>
  );
}

/* ─── status pill ──────────────────────────────────────────────────────────── */

function StatusPill({ state }) {
  const cfg = {
    idle:    { color: "rgba(255,255,255,0.25)", bg: "rgba(255,255,255,0.04)", label: "Idle" },
    syncing: { color: "#f59e0b",                bg: "rgba(245,158,11,0.08)",  label: "Syncing…" },
    done:    { color: "#22c55e",                bg: "rgba(34,197,94,0.08)",   label: "Up to date" },
    error:   { color: "#ef4444",                bg: "rgba(239,68,68,0.08)",   label: "Error" },
    demo:    { color: "#a78bfa",                bg: "rgba(167,139,250,0.08)", label: "Demo" },
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
  const { projects, activeId, setActiveId, active, addProject, removeProject, updateJql } = useProjects();

  const [snapshots,  setSnapshots]  = useState([]);
  const [analysis,   setAnalysis]   = useState(null);
  const [syncState,  setSyncState]  = useState("idle"); // idle | syncing | done | error | demo
  const [syncError,  setSyncError]  = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tweaksOpen,  setTweaksOpen]  = useState(false);
  const [newLabel,    setNewLabel]    = useState("");
  const [tweaks, setTweaks] = useState({ kpiStyle: "rich", density: "comfortable", aiTop: false });

  const pollRef = useRef(null);
  const activeProjectKey = active?.label || null;

  const resetBoard = useCallback(() => {
    setSnapshots([]);
    setAnalysis(null);
    setSyncState("idle");
    setSyncError(null);
  }, []);

  /* load data when active project changes */
  useEffect(() => {
    if (!activeProjectKey) return;
    let cancelled = false;
    Promise.all([fetchHistory(activeProjectKey), fetchLatest(activeProjectKey)])
      .then(([history, latest]) => {
        if (cancelled) return;
        const merged = mergeHistoryWithLatest(history, latest);
        setSnapshots(merged);
        setAnalysis(latest?.analysis || null);
        if (merged.length) setSyncState("done");
      })
      .catch(() => {
        // Missing snapshots are a normal pre-sync state.
      });
    return () => { cancelled = true; };
  }, [activeProjectKey]);

  /* sync */
  const handleSync = useCallback(async () => {
    if (!active || !creds.connected) return;
    const previousTimestamp = snapshots.at(-1)?.timestamp || null;
    clearTimeout(pollRef.current);
    setSyncState("syncing"); setSyncError(null);
    try {
      await postSync({ project: active.label, baseUrl: creds.baseUrl, email: creds.email, apiToken: creds.apiToken, jql: active.jql });
      /* poll for results */
      let attempts = 0;
      const poll = async () => {
        try {
          const [history, latest] = await Promise.all([
            fetchHistory(active.label),
            fetchLatest(active.label),
          ]);
          const merged = mergeHistoryWithLatest(history, latest);
          const latestTimestamp = latest?.timestamp || merged.at(-1)?.timestamp || null;
          if (latestTimestamp && latestTimestamp !== previousTimestamp) {
            setSnapshots(merged);
            setAnalysis(latest?.analysis || null);
            setSyncState("done");
            return;
          }
        } catch {
          // Keep polling through transient backend/network errors.
        }
        if (++attempts < POLL_MAX_ATTEMPTS) { pollRef.current = setTimeout(poll, POLL_INTERVAL_MS); }
        else {
          setSyncState("error");
          setSyncError("Sync did not produce a new snapshot");
        }
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

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#0e1016", color: "#e2e6ef", fontFamily: "'Inter', system-ui, sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0e1016; }
        @keyframes spin { to { transform: rotate(360deg); } }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
      `}</style>

      {sidebarOpen && (
        <Sidebar
          creds={creds}
          onConnect={() => creds.connect()}
          activeProject={active}
          onJqlChange={jql => active && updateJql(active.id, jql)}
          onDemo={handleDemo}
        />
      )}

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* App bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 14px", height: 48, borderBottom: "1px solid rgba(255,255,255,0.06)", flexShrink: 0, position: "relative" }}>
          {/* Hamburger */}
          <button
            aria-label={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
            title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
            onClick={() => setSidebarOpen(v => !v)}
            style={{ width: 30, height: 30, border: "1px solid rgba(255,255,255,0.08)", borderRadius: 7, background: "transparent", color: "rgba(255,255,255,0.45)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect y="2" width="14" height="1.5" rx="1" fill="currentColor"/><rect y="6.25" width="14" height="1.5" rx="1" fill="currentColor"/><rect y="10.5" width="14" height="1.5" rx="1" fill="currentColor"/></svg>
          </button>

          {/* Logo */}
          <span style={{ fontSize: "0.88rem", fontWeight: 800, letterSpacing: "-0.02em", color: "#fff", whiteSpace: "nowrap" }}>
            AI <span style={{ color: "#4f7cff" }}>Delivery</span> Analyst
          </span>

          {/* Project tabs */}
          <div style={{ display: "flex", alignItems: "center", gap: 2, flex: 1, overflow: "hidden", marginLeft: 6 }}>
            {projects.map(p => (
              <button key={p.id} onClick={() => { resetBoard(); setActiveId(p.id); }} style={{
                padding: "4px 10px", border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.76rem", fontWeight: 600, whiteSpace: "nowrap",
                background: p.id === activeId ? "rgba(79,124,255,0.15)" : "transparent",
                color: p.id === activeId ? "#4f7cff" : "rgba(255,255,255,0.4)",
              }}>{p.label}
                {p.id === activeId && (
                  <span onClick={e => { e.stopPropagation(); resetBoard(); removeProject(p.id); }} style={{ marginLeft: 5, opacity: 0.4, fontSize: "0.7rem" }}>✕</span>
                )}
              </button>
            ))}
            {/* Add project */}
            <div style={{ display: "flex", gap: 4, marginLeft: 4 }}>
              <input value={newLabel} onChange={e => setNewLabel(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddProject()}
                placeholder="Add project…" style={{ height: 26, borderRadius: 6, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.04)", color: "#e2e6ef", padding: "0 8px", fontSize: "0.73rem", outline: "none", width: 110, fontFamily: "inherit" }} />
              <button onClick={handleAddProject} style={{ height: 26, padding: "0 10px", border: "1px solid rgba(79,124,255,0.3)", borderRadius: 6, background: "rgba(79,124,255,0.08)", color: "rgba(79,124,255,0.8)", fontSize: "0.73rem", cursor: "pointer" }}>+</button>
            </div>
          </div>

          {/* Right side */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
            <StatusPill state={syncState} />
            {syncError && <span style={{ fontSize: "0.7rem", color: "#ef4444", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{syncError}</span>}
            <button onClick={handleSync} disabled={!active || !creds.connected || syncState === "syncing"}
              style={{ height: 28, padding: "0 14px", border: "1px solid rgba(79,124,255,0.35)", borderRadius: 7, background: "rgba(79,124,255,0.1)", color: "#4f7cff", fontSize: "0.76rem", fontWeight: 600, cursor: "pointer", opacity: (!active || !creds.connected) ? 0.4 : 1, transition: "opacity 0.15s" }}>
              ↻ Sync
            </button>
            {/* Tweaks toggle */}
            <button onClick={() => setTweaksOpen(v => !v)} style={{ width: 28, height: 28, border: "1px solid rgba(255,255,255,0.08)", borderRadius: 7, background: tweaksOpen ? "rgba(255,255,255,0.06)" : "transparent", color: "rgba(255,255,255,0.4)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><circle cx="6.5" cy="6.5" r="2" stroke="currentColor" strokeWidth="1.3"/><path d="M6.5 1v1.5M6.5 10.5V12M1 6.5h1.5M10.5 6.5H12M2.4 2.4l1.06 1.06M9.54 9.54l1.06 1.06M9.54 3.46L8.48 4.52M3.46 9.54l-1.06 1.06" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
            </button>
          </div>

          {tweaksOpen && <TweaksPanel tweaks={tweaks} setTweaks={setTweaks} onClose={() => setTweaksOpen(false)} />}
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflow: "auto", padding: compact ? "14px 16px" : "20px 22px", display: "flex", flexDirection: "column", gap: compact ? 14 : 20 }}>

          {/* No project selected + no demo data */}
          {!active && !hasData && (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>📊</div>
                <p style={{ fontSize: "0.95rem", color: "rgba(255,255,255,0.4)", marginBottom: 6 }}>No project selected</p>
                <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.22)" }}>Add a project in the tab bar above, or load demo data from the sidebar.</p>
              </div>
            </div>
          )}

          {/* AI panel (top position) */}
          {(active || hasData) && tweaks.aiTop && (
            <AIPanel analysis={analysis} prominent={!!analysis} />
          )}

          {/* KPI grid — show when there's an active project OR demo data loaded */}
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

          {/* AI panel (bottom position, default) */}
          {(active || hasData) && !tweaks.aiTop && (
            <AIPanel analysis={analysis} prominent={!!analysis} />
          )}

          {/* No data hint — project selected but nothing synced yet */}
          {active && !hasData && syncState === "idle" && (
            <div style={{ padding: "12px 16px", borderRadius: 10, background: "rgba(79,124,255,0.04)", border: "1px solid rgba(79,124,255,0.12)", fontSize: "0.8rem", color: "rgba(255,255,255,0.35)", lineHeight: 1.6 }}>
              Connect your Jira and click <strong style={{ color: "rgba(255,255,255,0.55)" }}>↻ Sync</strong> to pull metrics — or load demo data from the sidebar.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
