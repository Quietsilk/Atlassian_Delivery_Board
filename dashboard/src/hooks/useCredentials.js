import { useState, useCallback } from "react";

const KEYS = { baseUrl: "ada:baseUrl", email: "ada:email", token: "ada:token" };
const ls = (k, fb = "") => { try { return localStorage.getItem(k) || fb; } catch { return fb; } };
const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch {} };

export function useCredentials() {
  const [baseUrl,   setBaseUrlRaw]   = useState(() => ls(KEYS.baseUrl));
  const [email,     setEmailRaw]     = useState(() => ls(KEYS.email));
  const [apiToken,  setApiTokenRaw]  = useState(() => ls(KEYS.token));
  const [connected, setConnected]    = useState(false);
  const [connMsg,   setConnMsg]      = useState("Fill in the fields and click Connect.");

  const set = (setter, lsKey) => (v) => { setter(v); lsSet(lsKey, v); setConnected(false); };
  const setBaseUrl  = set(setBaseUrlRaw,  KEYS.baseUrl);
  const setEmail    = set(setEmailRaw,    KEYS.email);
  const setApiToken = set(setApiTokenRaw, KEYS.token);

  const connect = useCallback(() => {
    if (!baseUrl || !email || !apiToken) { setConnMsg("Fill in URL, Email and API Token."); return false; }
    if (!/^https:\/\/.+/i.test(baseUrl))   { setConnMsg("URL must start with https://"); return false; }
    if (!/^\S+@\S+\.\S+$/.test(email))     { setConnMsg("Enter a valid email."); return false; }
    setConnected(true);
    setConnMsg("Connected to " + baseUrl);
    return true;
  }, [baseUrl, email, apiToken]);

  return { baseUrl, email, apiToken, connected, connMsg, setBaseUrl, setEmail, setApiToken, connect };
}
