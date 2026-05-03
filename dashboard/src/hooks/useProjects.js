import { useState, useCallback } from "react";

const LS_KEY = "ada:projects-v2";

function load() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || []; } catch { return []; }
}
function save(v) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(v)); } catch {}
}

export function useProjects() {
  const [projects, setProjects] = useState(() => load());
  const [activeId, setActiveId] = useState(() => load()[0]?.id || null);

  const addProject = useCallback((label, jql) => {
    const id = "p-" + Date.now();
    const p = { id, label, jql: jql || `project = "${label}" ORDER BY updated DESC` };
    setProjects(prev => { const next = [...prev, p]; save(next); return next; });
    setActiveId(id);
    return id;
  }, []);

  const removeProject = useCallback((id) => {
    setProjects(prev => {
      const next = prev.filter(p => p.id !== id);
      save(next);
      return next;
    });
    setActiveId(prev => prev === id ? (projects.find(p => p.id !== id)?.id || null) : prev);
  }, [projects]);

  const updateJql = useCallback((id, jql) => {
    setProjects(prev => {
      const next = prev.map(p => p.id === id ? { ...p, jql } : p);
      save(next);
      return next;
    });
  }, []);

  const active = projects.find(p => p.id === activeId) || null;

  return { projects, activeId, setActiveId, active, addProject, removeProject, updateJql };
}
