import { useState } from "react";

/* ── Field ──────────────────────────────────────────────────────────────────── */
function Field({ label, children }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: "0.67rem", fontWeight: 600, color: "rgba(255,255,255,0.3)", letterSpacing: "0.03em" }}>
        {label}
      </span>
      {children}
    </div>
  );
}

const baseInput = {
  height: 32, borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.08)",
  background: "rgba(0,0,0,0.25)", color: "#e2e6ef",
  padding: "0 10px", fontSize: "0.78rem",
  fontFamily: "'Inter', system-ui, sans-serif",
  outline: "none", width: "100%",
  transition: "border-color 0.15s, background 0.15s",
};

function onFocus(e) {
  e.target.style.borderColor = "rgba(79,124,255,0.5)";
  e.target.style.background  = "rgba(79,124,255,0.04)";
}
function onBlur(e) {
  e.target.style.borderColor = "rgba(255,255,255,0.08)";
  e.target.style.background  = "rgba(0,0,0,0.25)";
}

/* ── Sidebar ────────────────────────────────────────────────────────────────── */
export default function Sidebar({ creds, onConnect, onDemo }) {
  const [showToken, setShowToken] = useState(false);

  const connected = creds.connected;
  const host = creds.baseUrl
    ? creds.baseUrl.replace(/^https?:\/\//, "").replace(/\/$/, "")
    : "";

  return (
    <aside style={{
      width: 264, flexShrink: 0,
      background: "rgba(255,255,255,0.016)",
      borderRight: "1px solid rgba(255,255,255,0.05)",
      display: "flex", flexDirection: "column", minHeight: "100vh",
    }}>
      <div style={{ display: "flex", flexDirection: "column", flex: 1, overflowY: "auto", overflowX: "hidden" }}>

        {/* ── Jira Connection ──────────────────────────────── */}
        <div style={{ padding: "18px 16px 16px" }}>
          <div style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.22)", marginBottom: 12 }}>
            Jira Connection
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>

            <Field label="URL">
              <input type="url" autoComplete="url" placeholder="https://company.atlassian.net"
                value={creds.baseUrl} onChange={e => creds.setBaseUrl(e.target.value)}
                style={baseInput} onFocus={onFocus} onBlur={onBlur} />
            </Field>

            <Field label="Email">
              <input type="email" autoComplete="username" placeholder="you@company.com"
                value={creds.email} onChange={e => creds.setEmail(e.target.value)}
                style={baseInput} onFocus={onFocus} onBlur={onBlur} />
            </Field>

            <Field label="API Token">
              <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                <input
                  type={showToken ? "text" : "password"}
                  autoComplete="current-password"
                  aria-label="API Token"
                  placeholder="Atlassian API token"
                  value={creds.apiToken} onChange={e => creds.setApiToken(e.target.value)}
                  style={{ ...baseInput, paddingRight: 44 }}
                  onFocus={onFocus} onBlur={onBlur}
                />
                <div style={{ position: "absolute", right: 0, top: 0, bottom: 0, display: "flex", alignItems: "center", paddingRight: 8 }}>
                  <button type="button" onClick={() => setShowToken(v => !v)} style={{
                    background: "none", border: "none", color: "rgba(255,255,255,0.3)",
                    fontSize: "0.68rem", fontWeight: 600, cursor: "pointer",
                    padding: "0 4px", fontFamily: "inherit", letterSpacing: "0.02em",
                    transition: "color 0.15s",
                  }}
                  onMouseEnter={e => e.target.style.color = "rgba(255,255,255,0.6)"}
                  onMouseLeave={e => e.target.style.color = "rgba(255,255,255,0.3)"}
                  >{showToken ? "Hide" : "Show"}</button>
                </div>
              </div>
            </Field>

            {/* Connect / Connected button */}
            <button type="button" onClick={onConnect} style={{
              height: 34, marginTop: 2, borderRadius: 8,
              fontSize: "0.8rem", fontWeight: 700, cursor: "pointer",
              width: "100%", fontFamily: "inherit",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              transition: "all 0.2s",
              ...(connected
                ? { border: "1px solid rgba(34,197,94,0.3)", background: "rgba(34,197,94,0.08)", color: "#22c55e" }
                : { border: "1px solid rgba(79,124,255,0.4)", background: "rgba(79,124,255,0.12)", color: "#e2e6ef" }
              ),
            }}>
              {connected ? (
                <>
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <circle cx="5" cy="5" r="4" fill="rgba(34,197,94,0.2)" stroke="#22c55e" strokeWidth="1"/>
                    <path d="M2.5 5l2 2 3-3" stroke="#22c55e" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Connected
                </>
              ) : "Connect"}
            </button>

            {/* Status pill — domain shown when connected */}
            {connected && host && (
              <div style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 10px", borderRadius: 7,
                background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.12)",
              }}>
                <div style={{
                  width: 5, height: 5, borderRadius: "50%", flexShrink: 0,
                  background: "#22c55e", boxShadow: "0 0 5px rgba(34,197,94,0.7)",
                }} />
                <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {host}
                </span>
              </div>
            )}

          </div>
        </div>

        {/* ── Divider ─────────────────────────────────────── */}
        <div style={{ height: 1, background: "rgba(255,255,255,0.05)", margin: "0 16px" }} />

        {/* ── Demo ─────────────────────────────────────────── */}
        <div style={{ padding: "16px 16px", marginTop: "auto" }}>
          <button type="button" onClick={onDemo} style={{
            width: "100%", height: 30,
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 8, background: "transparent",
            color: "rgba(255,255,255,0.3)", fontSize: "0.74rem", fontWeight: 500,
            cursor: "pointer", fontFamily: "inherit", letterSpacing: "0.01em",
            transition: "color 0.15s, border-color 0.15s, background 0.15s",
          }}
          onMouseEnter={e => {
            e.currentTarget.style.color = "rgba(255,255,255,0.65)";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)";
            e.currentTarget.style.background = "rgba(255,255,255,0.03)";
          }}
          onMouseLeave={e => {
            e.currentTarget.style.color = "rgba(255,255,255,0.3)";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
            e.currentTarget.style.background = "transparent";
          }}
          >⚡ Load demo data</button>
        </div>

      </div>
    </aside>
  );
}
