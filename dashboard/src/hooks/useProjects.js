import { useState, useCallback } from "react";

const LS_KEY        = "ada:projects-v2";
const LS_ACTIVE_KEY = "ada:activeId";

function load() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || []; } catch { return []; }
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

  const addProject = useCallback((label, jql) => {
    const id = "p-" + Date.now();
    const p = { id, label, jql: jql || `project = "${label}" ORDER BY updated DESC` };
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
