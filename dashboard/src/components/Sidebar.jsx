import { useState } from "react";
import { font, radius, transition } from "../tokens";
import { useT } from "../context/ThemeContext";

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
  trello: {
    id: "trello", name: "Trello", quality: "high",
    color: "#0079BF", colorBg: "rgba(0,121,191,0.1)", colorBorder: "rgba(0,121,191,0.3)",
    logo: (
      <svg width="18" height="18" viewBox="0 0 32 32" fill="none">
        <rect x="1" y="1" width="30" height="30" rx="5" fill="#0079BF"/>
        <rect x="4.5" y="4.5" width="10" height="18" rx="2" fill="white"/>
        <rect x="17.5" y="4.5" width="10" height="12" rx="2" fill="white"/>
      </svg>
    ),
    fields: [
      { id: "apiKey",  label: "API Key",  type: "password", placeholder: "Trello API key",       required: true },
      { id: "token",   label: "Token",    type: "password", placeholder: "Trello OAuth token",   required: true },
      { id: "boardId", label: "Board ID", type: "text",     placeholder: "Board ID from URL",    required: true },
    ],
    hint: "trello.com/app-key → copy API Key, then click Token link",
    qualityNote: "Action history · P50/P85 · Flow Efficiency",
    caveat: null,
  },
};

// ── SourcePicker ──────────────────────────────────────────────────────────────
function SourcePicker({ value, onChange }) {
  const T = useT();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ fontSize: font.size.xxs, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: T.textFaint }}>
        Data Source
      </span>
      <div style={{ display: "flex", padding: 2, borderRadius: radius.md, border: `1px solid ${T.border}`, background: T.bgCard }}>
        {Object.values(SOURCES).map(src => {
          const active = value === src.id;
          return (
            <button key={src.id} type="button" onClick={() => onChange(src.id)} style={{
              flex: 1,
              display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
              padding: "7px 8px", borderRadius: radius.sm,
              border: "none",
              background: active ? T.brandBg : "transparent",
              cursor: "pointer", transition: `all ${transition.fast}`,
              position: "relative", overflow: "hidden", fontFamily: "inherit",
            }}>
              {src.logo}
              <span style={{ fontSize: font.size.base, fontWeight: 700, color: active ? T.brand : T.textMuted }}>{src.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── InputField ────────────────────────────────────────────────────────────────
function InputField({ label, type, placeholder, value, onChange }) {
  const T = useT();
  const [show,        setShow]        = useState(false);
  const [focused,     setFocused]     = useState(false);
  const [showHovered, setShowHovered] = useState(false);
  const isPassword = type === "password";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: font.size.xs, fontWeight: 600, color: T.textMuted, letterSpacing: "0.03em" }}>{label}</span>
      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        <input
          type={isPassword && !show ? "password" : "text"}
          placeholder={placeholder}
          value={value}
          onChange={e => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{
            flex: 1, height: 32, borderRadius: radius.input,
            border: `1px solid ${focused ? T.brandFocus : T.borderHi}`,
            background: focused ? T.brandGlow : T.bgInput,
            color: T.text, padding: isPassword ? "0 44px 0 10px" : "0 10px",
            fontSize: font.size.base, fontFamily: "inherit", outline: "none", width: "100%",
            transition: `border-color ${transition.fast}, background ${transition.fast}`,
          }}
        />
        {isPassword && (
          <button type="button" onClick={() => setShow(v => !v)} style={{
            position: "absolute", right: 8, background: "none", border: "none",
            color: showHovered ? T.textSec : T.textMuted,
            fontSize: "0.68rem", fontWeight: 600,
            cursor: "pointer", fontFamily: "inherit",
            transition: `color ${transition.fast}`,
          }}
          onMouseEnter={() => setShowHovered(true)}
          onMouseLeave={() => setShowHovered(false)}
          >{show ? "Hide" : "Show"}</button>
        )}
      </div>
    </div>
  );
}

// ── ConnectForm ───────────────────────────────────────────────────────────────
function ConnectForm({ source, savedValues, connected, onConnect }) {
  const T = useT();
  const src = SOURCES[source] || SOURCES.jira;
  const [values,     setValues]     = useState(() => savedValues || {});
  const [connecting, setConnecting] = useState(false);

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
      <div style={{ fontSize: font.size.xs, color: T.textFaint, lineHeight: 1.5, padding: "7px 9px", borderRadius: radius.sm, background: T.bgCardHov, border: `1px solid ${T.borderSub}` }}>
        {src.hint}
      </div>

      {/* Caveat for medium quality sources */}
      {src.caveat && (
        <div style={{ fontSize: font.size.xs, color: T.warn, lineHeight: 1.5, padding: "5px 9px", borderRadius: radius.sm, background: T.warnBg, border: `1px solid ${T.warnBdr}` }}>
          {src.caveat}
        </div>
      )}

      {/* Connect button */}
      <button type="button" onClick={handleConnect} disabled={!allFilled || connecting} style={{
        height: 34, borderRadius: radius.input, width: "100%", fontFamily: "inherit",
        border: connected ? `1px solid ${T.goodBdr}` : "none",
        background: connected ? T.goodBg : T.brand,
        color: connected ? T.good : "#fff",
        fontSize: "0.8rem", fontWeight: 700,
        cursor: allFilled && !connecting ? "pointer" : "not-allowed",
        opacity: !allFilled && !connecting ? 0.5 : 1,
        display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
        transition: `all ${transition.normal}`,
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
              <circle cx="5" cy="5" r="4" fill={T.goodBg} stroke={T.good} strokeWidth="1"/>
              <path d="M2.5 5l2 2 3-3" stroke={T.good} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Connected to {src.name}
          </>
        ) : `Connect ${src.name}`}
      </button>

    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
export default function Sidebar({ creds, onDemo }) {
  const T = useT();
  const src = SOURCES[creds.source] || SOURCES.jira;
  const [demoHovered, setDemoHovered] = useState(false);
  return (
    <aside style={{
      width: 268, flexShrink: 0,
      background: T.bgSidebar,
      borderRight: `1px solid ${T.border}`,
      display: "flex", flexDirection: "column", minHeight: "100vh",
    }}>
      <style>{`
        @keyframes fadeSlide { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

      <div style={{ display: "flex", flexDirection: "column", flex: 1, overflowY: "auto", overflowX: "hidden", padding: "18px 16px", gap: 16 }}>

        {/* ── Source picker ──────────────────────────────────── */}
        <SourcePicker value={creds.source} onChange={creds.setSource} />

        <div style={{ height: 1, background: T.borderSub }} />

        {/* ── Connection form ────────────────────────────────── */}
        <div>
          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: font.size.xxs, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: T.textFaint }}>
              {src.name} Connection
            </span>
          </div>
          <ConnectForm
            key={src.id}
            source={src.id}
            savedValues={creds.currentCreds}
            connected={creds.connected}
            onConnect={creds.connect}
          />
        </div>

        <div style={{ height: 1, background: T.borderSub }} />

        {/* ── Demo ───────────────────────────────────────────── */}
        <button type="button" onClick={onDemo} style={{
          height: 32, border: `1px solid ${T.border}`, borderRadius: radius.input,
          background: demoHovered ? T.bgCardHov : T.bgCard, color: demoHovered ? T.textSec : T.textMuted,
          fontSize: "0.74rem", fontWeight: 500, cursor: "pointer", fontFamily: "inherit",
          letterSpacing: "0.01em", transition: `color ${transition.fast}`,
        }}
        onMouseEnter={() => setDemoHovered(true)}
        onMouseLeave={() => setDemoHovered(false)}
        >Load demo data</button>

      </div>
    </aside>
  );
}
