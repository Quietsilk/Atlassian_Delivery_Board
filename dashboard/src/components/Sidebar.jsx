import { useState, useEffect } from "react";

// ── Source definitions ────────────────────────────────────────────────────────
const SOURCES = {
  jira: {
    id: "jira", name: "Jira", quality: "high",
    color: "#2684FF", colorBg: "rgba(38,132,255,0.1)", colorBorder: "rgba(38,132,255,0.3)",
    logo: (
      <svg width="18" height="18" viewBox="0 0 32 32" fill="none">
        <path d="M15.89 2.16L8.3 9.75a1.07 1.07 0 000 1.51l5.27 5.27 7.85-7.85a1.07 1.07 0 000-1.51L16.9 2.16a.72.72 0 00-1.01 0z" fill="#2684FF"/>
        <path d="M15.89 15.14L8.3 22.73a1.07 1.07 0 000 1.51l5.27 5.27 7.85-7.85a1.07 1.07 0 000-1.51l-4.52-4.52z" fill="#2684FF" opacity="0.7"/>
      </svg>
    ),
    fields: [
      { id: "baseUrl",  label: "URL",       type: "url",      placeholder: "https://company.atlassian.net", required: true },
      { id: "email",    label: "Email",     type: "email",    placeholder: "you@company.com",               required: true },
      { id: "apiToken", label: "API Token", type: "password", placeholder: "Atlassian API token",           required: true },
    ],
    hint: "id.atlassian.com → Security → API tokens",
    qualityNote: "Full changelog · P50/P85 · Flow Efficiency",
    caveat: null,
  },
  linear: {
    id: "linear", name: "Linear", quality: "high",
    color: "#5E6AD2", colorBg: "rgba(94,106,210,0.1)", colorBorder: "rgba(94,106,210,0.3)",
    logo: (
      <svg width="18" height="18" viewBox="0 0 100 100" fill="none">
        <path d="M1.22 61.5L38.5 98.78a50 50 0 01-37.28-37.28zM0 50.15L49.85 100A50 50 0 010 50.15zM13.55 15.35L84.65 86.45A50 50 0 0013.55 15.35zM26.1 4.55l69.35 69.35A50 50 0 0026.1 4.55zM50.15 0L100 49.85A50 50 0 0050.15 0z" fill="#5E6AD2"/>
      </svg>
    ),
    fields: [
      { id: "apiKey", label: "API Key", type: "password", placeholder: "lin_api_••••••••••",          required: true },
      { id: "teamId", label: "Team ID", type: "text",     placeholder: "Optional — blank = all teams", required: false },
    ],
    hint: "Settings → API → Personal API keys → Create key",
    qualityNote: "Full history · P50/P85 · Flow Efficiency",
    caveat: null,
  },
  asana: {
    id: "asana", name: "Asana", quality: "medium",
    color: "#F06A6A", colorBg: "rgba(240,106,106,0.1)", colorBorder: "rgba(240,106,106,0.3)",
    logo: (
      <svg width="18" height="18" viewBox="0 0 100 100" fill="none">
        <circle cx="50" cy="27" r="20" fill="#F06A6A"/>
        <circle cx="20" cy="70" r="20" fill="#F06A6A"/>
        <circle cx="80" cy="70" r="20" fill="#F06A6A"/>
      </svg>
    ),
    fields: [
      { id: "accessToken", label: "Personal Access Token",   type: "password", placeholder: "0/••••••••••••••",   required: true },
      { id: "workspaceId", label: "Workspace / Project GID", type: "text",     placeholder: "Project GID from URL", required: true },
    ],
    hint: "My Profile → Apps → Manage Developer Apps → New token",
    qualityNote: "Limited history · TODO→DONE only",
    caveat: "Story-based changelog — cycle time is approximate, Flow Efficiency unavailable",
  },
  clickup: {
    id: "clickup", name: "ClickUp", quality: "medium",
    color: "#7B68EE", colorBg: "rgba(123,104,238,0.1)", colorBorder: "rgba(123,104,238,0.3)",
    logo: (
      <svg width="18" height="18" viewBox="0 0 100 100" fill="none">
        <path d="M10 65L30 45l20 22 20-22 20 20" stroke="#7B68EE" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        <path d="M10 45L30 25l20 22 20-22 20 20" stroke="#7B68EE" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.5"/>
      </svg>
    ),
    fields: [
      { id: "apiToken", label: "API Token", type: "password", placeholder: "pk_••••••••••••••••", required: true },
      { id: "teamId",   label: "Team ID",   type: "text",     placeholder: "Your ClickUp Team ID", required: true },
      { id: "listId",   label: "List ID",   type: "text",     placeholder: "Optional — specific list", required: false },
    ],
    hint: "Settings → Apps → API → Generate token",
    qualityNote: "Custom statuses · partial history",
    caveat: "Custom statuses may need mapping. History may miss transitions.",
  },
};

// ── localStorage helpers ──────────────────────────────────────────────────────
const LS_STARTED = "ada:started-statuses";
const LS_DONE    = "ada:done-statuses";
const ls    = (k, fb) => { try { return localStorage.getItem(k) || fb; } catch { return fb; } };
const lsSet = (k, v)  => { try { localStorage.setItem(k, v); }           catch {} };

// ── QualityBadge ──────────────────────────────────────────────────────────────
function QualityBadge({ quality }) {
  const high = quality === "high";
  return (
    <span style={{
      fontSize: "0.62rem", fontWeight: 700, padding: "2px 7px", borderRadius: 4,
      background: high ? "rgba(34,197,94,0.08)"  : "rgba(245,158,11,0.08)",
      border:     high ? "1px solid rgba(34,197,94,0.2)" : "1px solid rgba(245,158,11,0.2)",
      color:      high ? "#22c55e" : "#f59e0b",
      letterSpacing: "0.03em",
    }}>
      {high ? "High quality" : "Medium quality"}
    </span>
  );
}

// ── SourcePicker ──────────────────────────────────────────────────────────────
function SourcePicker({ value, onChange }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.22)" }}>
        Data Source
      </span>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
        {Object.values(SOURCES).map(src => {
          const active = value === src.id;
          return (
            <button key={src.id} type="button" onClick={() => onChange(src.id)} style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "9px 10px", borderRadius: 9,
              border: `1px solid ${active ? src.colorBorder : "rgba(255,255,255,0.07)"}`,
              background: active ? src.colorBg : "rgba(255,255,255,0.02)",
              cursor: "pointer", transition: "all 0.15s",
              position: "relative", overflow: "hidden", fontFamily: "inherit",
            }}>
              {active && (
                <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: src.color, borderRadius: "9px 9px 0 0" }} />
              )}
              {src.logo}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 1 }}>
                <span style={{ fontSize: "0.78rem", fontWeight: 700, color: active ? src.color : "rgba(255,255,255,0.35)" }}>{src.name}</span>
                <span style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.22)" }}>{src.quality} quality</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── InputField ────────────────────────────────────────────────────────────────
function InputField({ label, type, placeholder, value, onChange }) {
  const [show, setShow]       = useState(false);
  const [focused, setFocused] = useState(false);
  const isPassword = type === "password";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: "0.67rem", fontWeight: 600, color: "rgba(255,255,255,0.3)", letterSpacing: "0.03em" }}>{label}</span>
      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        <input
          type={isPassword && !show ? "password" : "text"}
          placeholder={placeholder}
          value={value}
          onChange={e => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{
            flex: 1, height: 32, borderRadius: 8,
            border: `1px solid ${focused ? "rgba(79,124,255,0.5)" : "rgba(255,255,255,0.08)"}`,
            background: focused ? "rgba(79,124,255,0.04)" : "rgba(0,0,0,0.25)",
            color: "#e2e6ef", padding: isPassword ? "0 44px 0 10px" : "0 10px",
            fontSize: "0.78rem", fontFamily: "inherit", outline: "none", width: "100%",
            transition: "border-color 0.15s, background 0.15s",
          }}
        />
        {isPassword && (
          <button type="button" onClick={() => setShow(v => !v)} style={{
            position: "absolute", right: 8, background: "none", border: "none",
            color: "rgba(255,255,255,0.3)", fontSize: "0.68rem", fontWeight: 600,
            cursor: "pointer", fontFamily: "inherit",
            transition: "color 0.15s",
          }}
          onMouseEnter={e => e.target.style.color = "rgba(255,255,255,0.6)"}
          onMouseLeave={e => e.target.style.color = "rgba(255,255,255,0.3)"}
          >{show ? "Hide" : "Show"}</button>
        )}
      </div>
    </div>
  );
}

// ── ConnectForm ───────────────────────────────────────────────────────────────
function ConnectForm({ source, savedValues, connected, onConnect }) {
  const src = SOURCES[source];
  const [values,     setValues]     = useState(() => savedValues || {});
  const [connecting, setConnecting] = useState(false);

  // Reset form values when source changes
  useEffect(() => { setValues(savedValues || {}); }, [source]); // eslint-disable-line react-hooks/exhaustive-deps

  const allFilled = src.fields.filter(f => f.required).every(f => values[f.id]?.trim());

  function handleConnect() {
    if (!allFilled || connecting) return;
    setConnecting(true);
    setTimeout(() => {
      setConnecting(false);
      onConnect(source, values);
    }, 1200);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, animation: "fadeSlide 0.18s ease" }} key={source}>
      {src.fields.map(f => (
        <InputField key={f.id} label={f.label} type={f.type} placeholder={f.placeholder}
          value={values[f.id] || ""}
          onChange={v => setValues(prev => ({ ...prev, [f.id]: v }))} />
      ))}

      {/* Hint */}
      <div style={{ fontSize: "0.67rem", color: "rgba(255,255,255,0.22)", lineHeight: 1.5, padding: "5px 9px", borderRadius: 6, background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.06)" }}>
        💡 {src.hint}
      </div>

      {/* Caveat for medium quality sources */}
      {src.caveat && (
        <div style={{ fontSize: "0.67rem", color: "#f59e0b", lineHeight: 1.5, padding: "5px 9px", borderRadius: 6, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)" }}>
          ⚠ {src.caveat}
        </div>
      )}

      {/* Connect button */}
      <button type="button" onClick={handleConnect} disabled={!allFilled || connecting} style={{
        height: 34, borderRadius: 8, width: "100%", fontFamily: "inherit",
        border: `1px solid ${connected ? "rgba(34,197,94,0.3)" : src.colorBorder}`,
        background: connected ? "rgba(34,197,94,0.08)" : src.colorBg,
        color: connected ? "#22c55e" : src.color,
        fontSize: "0.8rem", fontWeight: 700,
        cursor: allFilled && !connecting ? "pointer" : "not-allowed",
        opacity: !allFilled && !connecting ? 0.5 : 1,
        display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
        transition: "all 0.2s",
      }}>
        {connecting ? (
          <>
            <svg width="12" height="12" viewBox="0 0 12 12" style={{ animation: "spin 0.8s linear infinite" }}>
              <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeDasharray="14 8" strokeLinecap="round"/>
            </svg>
            Connecting…
          </>
        ) : connected ? (
          <>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <circle cx="5" cy="5" r="4" fill="rgba(34,197,94,0.2)" stroke="#22c55e" strokeWidth="1"/>
              <path d="M2.5 5l2 2 3-3" stroke="#22c55e" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Connected to {src.name}
          </>
        ) : `Connect ${src.name}`}
      </button>

      {/* Connected status pill */}
      {connected && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 10px", borderRadius: 7, background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.12)" }}>
          <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#22c55e", flexShrink: 0, boxShadow: "0 0 5px rgba(34,197,94,0.7)" }} />
          <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {src.name} · {src.qualityNote}
          </span>
          <QualityBadge quality={src.quality} />
        </div>
      )}
    </div>
  );
}

// ── StatusMapping ─────────────────────────────────────────────────────────────
function StatusMapping() {
  const [started, setStarted] = useState(() => ls(LS_STARTED, "In Progress, In Development, Selected for Development"));
  const [done,    setDone]    = useState(() => ls(LS_DONE,    "Done, Closed, Resolved"));
  const [saved,   setSaved]   = useState(false);

  function handleSave() {
    lsSet(LS_STARTED, started);
    lsSet(LS_DONE,    done);
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  }

  const tag = (rgb) => ({
    display: "inline-flex", alignItems: "center",
    padding: "1px 7px", borderRadius: 4,
    background: `rgba(${rgb},0.12)`, border: `1px solid rgba(${rgb},0.25)`,
    fontSize: "0.67rem", fontWeight: 700, color: `rgb(${rgb})`,
    fontFamily: "'IBM Plex Mono', monospace",
  });

  const tareaStyle = {
    borderRadius: 7, border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(0,0,0,0.25)", color: "#e2e6ef",
    padding: "6px 10px", fontSize: "0.72rem",
    fontFamily: "'IBM Plex Mono', monospace",
    outline: "none", width: "100%", resize: "none",
    lineHeight: 1.5, transition: "border-color 0.15s",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.22)" }}>
        Status Mapping
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={tag("79,124,255")}>STARTED</span>
          <span style={{ fontSize: "0.67rem", color: "rgba(255,255,255,0.22)" }}>In Progress states</span>
        </div>
        <textarea rows={2} value={started} onChange={e => setStarted(e.target.value)} style={tareaStyle}
          onFocus={e => e.target.style.borderColor = "rgba(79,124,255,0.5)"}
          onBlur={e  => e.target.style.borderColor = "rgba(255,255,255,0.08)"} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={tag("34,197,94")}>DONE</span>
          <span style={{ fontSize: "0.67rem", color: "rgba(255,255,255,0.22)" }}>Completed states</span>
        </div>
        <textarea rows={2} value={done} onChange={e => setDone(e.target.value)} style={tareaStyle}
          onFocus={e => e.target.style.borderColor = "rgba(79,124,255,0.5)"}
          onBlur={e  => e.target.style.borderColor = "rgba(255,255,255,0.08)"} />
      </div>

      <div style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.22)", lineHeight: 1.5 }}>
        Comma-separated · case-insensitive
      </div>

      <button type="button" onClick={handleSave} style={{
        height: 30, borderRadius: 7, width: "100%", fontFamily: "inherit",
        border: `1px solid ${saved ? "rgba(34,197,94,0.3)" : "rgba(79,124,255,0.3)"}`,
        background: saved ? "rgba(34,197,94,0.08)" : "rgba(79,124,255,0.08)",
        color: saved ? "#22c55e" : "#4f7cff",
        fontSize: "0.76rem", fontWeight: 600, cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 5,
        transition: "all 0.2s",
      }}>
        {saved ? (
          <>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 5l2.5 2.5 4-4" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Saved
          </>
        ) : "Save mapping"}
      </button>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
export default function Sidebar({ creds, onDemo }) {
  const src = SOURCES[creds.source];
  return (
    <aside style={{
      width: 264, flexShrink: 0,
      background: "rgba(255,255,255,0.016)",
      borderRight: "1px solid rgba(255,255,255,0.05)",
      display: "flex", flexDirection: "column", minHeight: "100vh",
    }}>
      <style>{`
        @keyframes fadeSlide { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

      <div style={{ display: "flex", flexDirection: "column", flex: 1, overflowY: "auto", overflowX: "hidden", padding: "18px 16px", gap: 16 }}>

        {/* ── Source picker ──────────────────────────────────── */}
        <SourcePicker value={creds.source} onChange={creds.setSource} />

        <div style={{ height: 1, background: "rgba(255,255,255,0.05)" }} />

        {/* ── Connection form ────────────────────────────────── */}
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <span style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.22)" }}>
              {src.name} Connection
            </span>
            <QualityBadge quality={src.quality} />
          </div>
          <ConnectForm
            source={creds.source}
            savedValues={creds.currentCreds}
            connected={creds.connected}
            onConnect={creds.connect}
          />
        </div>

        <div style={{ height: 1, background: "rgba(255,255,255,0.05)" }} />

        {/* ── Status mapping ─────────────────────────────────── */}
        <StatusMapping />

        <div style={{ height: 1, background: "rgba(255,255,255,0.05)" }} />

        {/* ── Demo ───────────────────────────────────────────── */}
        <button type="button" onClick={onDemo} style={{
          height: 30, border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8,
          background: "transparent", color: "rgba(255,255,255,0.3)",
          fontSize: "0.74rem", fontWeight: 500, cursor: "pointer", fontFamily: "inherit",
          letterSpacing: "0.01em", transition: "color 0.15s, border-color 0.15s",
        }}
        onMouseEnter={e => { e.currentTarget.style.color = "rgba(255,255,255,0.65)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)"; }}
        onMouseLeave={e => { e.currentTarget.style.color = "rgba(255,255,255,0.3)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; }}
        >⚡ Load demo data</button>

      </div>
    </aside>
  );
}
