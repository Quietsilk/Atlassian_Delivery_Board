import { useCallback, useMemo, useState } from "react";

const LS_ACTIVE_KEY = "ada:activeProjectId";
const LEGACY_KEYS = ["ada:creds-v2", "ada:projects-v2", "ada:projects-v3", "ada:source"];

function loadActiveId() {
  try { return localStorage.getItem(LS_ACTIVE_KEY); } catch { return null; }
}

function clearLegacyStorage() {
  try { LEGACY_KEYS.forEach(key => localStorage.removeItem(key)); } catch { /* unavailable storage */ }
}

export function useProjects() {
  const [projects, setProjectsState] = useState([]);
  const [activeId, setActiveIdState] = useState(loadActiveId);

  const setProfiles = useCallback((profiles) => {
    clearLegacyStorage();
    const next = (profiles || []).map(profile => ({
      id: profile.id,
      profileId: profile.id,
      label: profile.label || profile.project,
      projectKey: profile.project,
      source: profile.source,
      methodology: profile.methodology,
      issueBaseUrl: profile.issueBaseUrl || null,
    }));
    setProjectsState(next);
    setActiveIdState(current => {
      const selected = next.some(item => item.id === current) ? current : (next[0]?.id || null);
      try {
        if (selected) localStorage.setItem(LS_ACTIVE_KEY, selected);
        else localStorage.removeItem(LS_ACTIVE_KEY);
      } catch { /* unavailable storage */ }
      return selected;
    });
  }, []);

  const setActiveId = useCallback((id) => {
    setActiveIdState(id);
    try {
      if (id) localStorage.setItem(LS_ACTIVE_KEY, id);
      else localStorage.removeItem(LS_ACTIVE_KEY);
    } catch { /* unavailable storage */ }
  }, []);

  const active = useMemo(
    () => projects.find(project => project.id === activeId) || null,
    [projects, activeId],
  );

  return { projects, activeId, setActiveId, active, setProfiles };
}
