import { useState, useCallback } from "react";

// ── localStorage helpers ───────────────────────────────────────────────────────
const LS_SOURCE = "ada:source";
const LS_CREDS  = "ada:creds-v2"; // { jira:{...}, linear:{...}, asana:{...}, clickup:{...} }

const ls    = (k, fb = null) => { try { return localStorage.getItem(k) || fb; } catch { return fb; } };
const lsSet = (k, v)         => { try { localStorage.setItem(k, v); }          catch {} };

function loadSaved() {
  try { return JSON.parse(localStorage.getItem(LS_CREDS)) || {}; } catch { return {}; }
}

// ── Required fields per source (optional fields excluded) ─────────────────────
const REQUIRED = {
  jira:    ["baseUrl", "email", "apiToken"],
  linear:  ["apiKey"],
  asana:   ["accessToken", "workspaceId"],
  clickup: ["apiToken", "teamId"],
};

export function hasRequired(source, vals) {
  return !!(vals && (REQUIRED[source] || []).every(k => vals[k]?.trim()));
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useCredentials() {
  const [source,     setSourceState] = useState(() => ls(LS_SOURCE) || "jira");
  const [savedCreds, setSavedCreds]  = useState(loadSaved);
  const [connected,  setConnected]   = useState(() => {
    const src  = ls(LS_SOURCE) || "jira";
    return hasRequired(src, loadSaved()[src]);
  });

  /** Switch active source; restores connected state from previously saved creds. */
  const setSource = useCallback((s) => {
    setSourceState(s);
    lsSet(LS_SOURCE, s);
    setSavedCreds(prev => {
      setConnected(hasRequired(s, prev[s]));
      return prev;
    });
  }, []);

  /** Save credentials for a source and mark as connected. */
  const connect = useCallback((src, values) => {
    setSavedCreds(prev => {
      const next = { ...prev, [src]: values };
      lsSet(LS_CREDS, JSON.stringify(next));
      return next;
    });
    setConnected(true);
  }, []);

  /** Saved credentials for the currently active source. */
  const currentCreds = savedCreds[source] || {};

  return { source, setSource, connected, connect, currentCreds };
}
