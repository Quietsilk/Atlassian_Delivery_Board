import { useState, useCallback } from "react";

const LS_KEY        = "ada:projects-v3";
const LS_ACTIVE_KEY = "ada:activeId";

function load() {
  try {
    const v3 = JSON.parse(localStorage.getItem(LS_KEY));
    if (v3) return v3;
    // Migrate from v2 — add default source
    const v2 = JSON.parse(localStorage.getItem("ada:projects-v2"));
    if (v2?.length) {
      const migrated = v2.map(p => ({ ...p, source: p.source || "jira" }));
      localStorage.setItem(LS_KEY, JSON.stringify(migrated));
      return migrated;
    }
    return [];
  } catch { return []; }
}
function save(v) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(v)); } catch { /* ignore storage errors */ }
}
function loadActiveId() {
  try { return localStorage.getItem(LS_ACTIVE_KEY) || null; } catch { return null; }
}
function saveActiveId(id) {
  try {
    if (id) localStorage.setItem(LS_ACTIVE_KEY, id);
    else     localStorage.removeItem(LS_ACTIVE_KEY);
  } catch { /* ignore storage errors */ }
}

export function useProjects() {
  const [projects, setProjects] = useState(() => load());
  const [activeId, setActiveIdState] = useState(() => {
    const saved  = loadActiveId();
    const loaded = load();
    // restore saved activeId only if the project still exists
    return (saved && loaded.find(p => p.id === saved)) ? saved : (loaded[0]?.id || null);
  });

  const setActiveId = useCallback((id) => {
    setActiveIdState(id);
    saveActiveId(id);
  }, []);

  const addProject = useCallback((label, source, jql) => {
    const id = "p-" + Date.now();
    const p = { id, label, source: source || "jira", jql: jql || `project = "${label}" ORDER BY updated DESC` };
    setProjects(prev => { const next = [...prev, p]; save(next); return next; });
    setActiveId(id);
    return id;
  }, [setActiveId]);

  const removeProject = useCallback((id) => {
    setProjects(prev => {
      const next = prev.filter(p => p.id !== id);
      save(next);
      return next;
    });
    const nextId = activeId === id
      ? (projects.find(p => p.id !== id)?.id || null)
      : activeId;
    setActiveId(nextId);
  }, [projects, activeId, setActiveId]);

  const active = projects.find(p => p.id === activeId) || null;

  return { projects, activeId, setActiveId, active, addProject, removeProject };
}
