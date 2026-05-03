import { useState } from "react";

const field = (label, props, wrapperStyle = {}) => (
  <div key={label || props.placeholder} style={{ display: "flex", flexDirection: "column", gap: 3, ...wrapperStyle }}>
    {label && <label style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.35)", fontWeight: 500 }}>{label}</label>}
    <input {...props} style={{ height: 30, borderRadius: 7, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.3)", color: "#e2e6ef", padding: "0 10px", fontSize: "0.78rem", outline: "none", width: "100%", fontFamily: "inherit", ...props.style }} />
  </div>
);

export default function Sidebar({ creds, onConnect, activeProject, onJqlChange, onDemo }) {
  const [showToken, setShowToken] = useState(false);

  return (
    <aside style={{
      width: 260, flexShrink: 0, overflow: "hidden",
      background: "rgba(255,255,255,0.018)",
      borderRight: "1px solid rgba(255,255,255,0.05)",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ width: 260, display: "flex", flexDirection: "column", flex: 1, overflow: "hidden auto", padding: "16px 14px", gap: 20 }}>

        {/* Jira connection */}
        <div>
          <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.25)", marginBottom: 10 }}>Jira Connection</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {field("URL",   { type: "url",      autoComplete: "url",      placeholder: "https://company.atlassian.net", value: creds.baseUrl,  onChange: e => creds.setBaseUrl(e.target.value) })}
            {field("Email", { type: "email",    autoComplete: "username", placeholder: "you@company.com",               value: creds.email,    onChange: e => creds.setEmail(e.target.value) })}
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <label style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.35)", fontWeight: 500 }}>API Token</label>
              <div style={{ display: "flex", gap: 6 }}>
                {field("", { type: showToken ? "text" : "password", autoComplete: "current-password", "aria-label": "API Token", placeholder: "Atlassian API token", value: creds.apiToken, onChange: e => creds.setApiToken(e.target.value) }, { flex: 1 })}
                <button type="button" onClick={() => setShowToken(v => !v)} style={{ height: 30, padding: "0 8px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 7, background: "rgba(255,255,255,0.04)", color: "rgba(255,255,255,0.4)", fontSize: "0.72rem", cursor: "pointer", flexShrink: 0 }}>{showToken ? "Hide" : "Show"}</button>
              </div>
            </div>
            <button type="button" onClick={onConnect} style={{ height: 30, marginTop: 2, border: "1px solid rgba(79,124,255,0.4)", borderRadius: 7, background: "rgba(79,124,255,0.1)", color: "#e2e6ef", fontSize: "0.78rem", fontWeight: 600, cursor: "pointer", alignSelf: "flex-start", padding: "0 14px" }}>{creds.connected ? "Connected" : "Connect"}</button>
            <p style={{ fontSize: "0.72rem", color: creds.connected ? "#22c55e" : "rgba(255,255,255,0.3)", lineHeight: 1.4 }}>{creds.connMsg}</p>
          </div>
        </div>

        {/* JQL */}
        <div>
          <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.25)", marginBottom: 10 }}>Active Query</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <label style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.35)", fontWeight: 500 }}>JQL</label>
            <input type="text" value={activeProject?.jql || ""} onChange={e => onJqlChange(e.target.value)}
              disabled={!activeProject}
              placeholder='project = "KEY" ORDER BY updated DESC'
              style={{ height: 30, borderRadius: 7, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.3)", color: "#e2e6ef", padding: "0 10px", fontSize: "0.72rem", outline: "none", width: "100%", fontFamily: "'IBM Plex Mono', monospace", opacity: activeProject ? 1 : 0.45 }} />
            {activeProject && <p style={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.25)" }}>Project: {activeProject.label}</p>}
          </div>
        </div>

        {/* Demo */}
        <div style={{ marginTop: "auto", paddingTop: 16, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <button type="button" onClick={onDemo} style={{ width: "100%", height: 30, border: "1px solid rgba(34,197,94,0.3)", borderRadius: 7, background: "rgba(34,197,94,0.06)", color: "rgba(255,255,255,0.5)", fontSize: "0.76rem", cursor: "pointer", transition: "color 0.15s, border-color 0.15s" }}>
            ⚡ Load demo data
          </button>
        </div>

      </div>
    </aside>
  );
}
