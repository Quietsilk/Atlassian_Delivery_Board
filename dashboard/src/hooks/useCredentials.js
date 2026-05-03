import { useState, useCallback } from "react";

const KEYS = { baseUrl: "ada:baseUrl", email: "ada:email", token: "ada:token" };
const ls = (k, fb = "") => { try { return localStorage.getItem(k) || fb; } catch { return fb; } };
const lsSet = (k, v) => {
  try {
    localStorage.setItem(k, v);
  } catch {
    return false;
  }
  return true;
};

function validate(baseUrl, email, apiToken) {
  if (!baseUrl || !email || !apiToken) return "Fill in URL, Email and API Token.";
  if (!/^https:\/\/.+/i.test(baseUrl)) return "URL must start with https://";
  if (!/^\S+@\S+\.\S+$/.test(email)) return "Enter a valid email.";
  return "";
}

export function useCredentials() {
  const [baseUrl,   setBaseUrlRaw]   = useState(() => ls(KEYS.baseUrl));
  const [email,     setEmailRaw]     = useState(() => ls(KEYS.email));
  const [apiToken,  setApiTokenRaw]  = useState(() => ls(KEYS.token));
  const [connected, setConnected]    = useState(() => !validate(ls(KEYS.baseUrl), ls(KEYS.email), ls(KEYS.token)));
  const [connMsg,   setConnMsg]      = useState(() => {
    const savedBaseUrl = ls(KEYS.baseUrl);
    return validate(savedBaseUrl, ls(KEYS.email), ls(KEYS.token)) || "Connected to " + savedBaseUrl;
  });

  const set = (setter, lsKey) => (v) => { setter(v); lsSet(lsKey, v); setConnected(false); };
  const setBaseUrl  = set(setBaseUrlRaw,  KEYS.baseUrl);
  const setEmail    = set(setEmailRaw,    KEYS.email);
  const setApiToken = set(setApiTokenRaw, KEYS.token);

  const connect = useCallback(() => {
    const error = validate(baseUrl, email, apiToken);
    if (error) { setConnMsg(error); return false; }
    setConnected(true);
    setConnMsg("Connected to " + baseUrl);
    return true;
  }, [baseUrl, email, apiToken]);

  return { baseUrl, email, apiToken, connected, connMsg, setBaseUrl, setEmail, setApiToken, connect };
}
