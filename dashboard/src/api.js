const BASE = "http://localhost:5678";

function normalizeSnapshot(snapshot) {
  if (!snapshot) return null;
  const metrics = snapshot.metrics || snapshot;
  return {
    timestamp: snapshot.timestamp || null,
    cycleTime: metrics.cycleTimeP50 ?? metrics.cycleTimeDays ?? metrics.cycleTime ?? 0,
    cycleTimeP85: metrics.cycleTimeP85 ?? 0,
    timeToMarket: metrics.timeToMarketP50 ?? metrics.timeToMarketDays ?? metrics.timeToMarket ?? 0,
    timeToMarketP85: metrics.timeToMarketP85 ?? 0,
    flowEfficiency: metrics.flowEfficiencyPercent ?? metrics.flowEfficiency ?? 0,
    reopened: metrics.reopenedCount ?? metrics.reopened ?? 0,
    wip: metrics.inProgressCount ?? metrics.wip ?? 0,
    backlogAging: metrics.backlogAgingDays ?? metrics.backlogAging ?? 0,
    analysis: metrics.analysis ?? snapshot.analysis ?? null,
  };
}

export async function fetchLatest(project) {
  const res = await fetch(`${BASE}/latest?project=${encodeURIComponent(project)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("HTTP " + res.status);
  const body = await res.json();
  if (!body.ok) throw new Error(body.error || "Server error");
  return normalizeSnapshot(body.snapshot);
}

export async function fetchHistory(project) {
  const res = await fetch(`${BASE}/history?project=${encodeURIComponent(project)}`);
  if (!res.ok) return [];
  const body = await res.json();
  return (body.snapshots || []).map(normalizeSnapshot).filter(Boolean);
}

export async function postSync({ project, baseUrl, email, apiToken, jql }) {
  const res = await fetch(`${BASE}/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project, baseUrl, email, apiToken, jql }),
  });
  if (!res.ok) throw new Error("Sync failed");
  return res.json();
}
