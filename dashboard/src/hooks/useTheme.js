import { useState, useCallback } from "react";
import { getTokens } from "../tokens";

const LS_KEY = "ada:theme";

export function useTheme() {
  const [mode, setMode] = useState(() => {
    try { return localStorage.getItem(LS_KEY) || "light"; } catch { return "light"; }
  });

  const toggleTheme = useCallback(() => {
    setMode(prev => {
      const next = prev === "dark" ? "light" : "dark";
      try { localStorage.setItem(LS_KEY, next); } catch { /* ignore storage errors */ }
      return next;
    });
  }, []);

  return { mode, T: getTokens(mode), toggleTheme };
}
