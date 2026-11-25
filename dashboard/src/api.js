const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...options,
    headers: options.body ? { "Content-Type": "application/json", ...(options.headers || {}) } : options.headers,
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(payload.error || `HTTP ${res.status}`);
    error.status = res.status;
    throw error;
  }
  return payload;
}

export async function fetchSession() { return request("/session"); }
export async function login(accessToken) {
  return request("/login", { method: "POST", body: JSON.stringify({ accessToken }) });
}
export async function logout() { return request("/logout", { method: "POST", body: "{}" }); }

function normalizeSnapshot(snapshot) {
  if (!snapshot) return null;
  const metrics = snapshot.metrics || snapshot;
  const hasFlowSample = Object.prototype.hasOwnProperty.call(metrics, "flowSampleSize");
  return {
    timestamp: snapshot.timestamp || null,
    cycleTime: metrics.cycleTimeP50 ?? metrics.cycleTimeDays ?? metrics.cycleTime ?? 0,
    cycleTimeP85: metrics.cycleTimeP85 ?? 0,
    timeToMarket: metrics.timeToMarketP50 ?? metrics.timeToMarketDays ?? metrics.timeToMarket ?? 0,
    timeToMarketP85: metrics.timeToMarketP85 ?? 0,
    flowEfficiency: metrics.flowEfficiencyPercent ?? metrics.flowEfficiency ?? 0,
    sprintCompletion: metrics.sprintCompletionPercent ?? metrics.sprintCompletion ?? null,
    sprintCommittedCount: metrics.sprintCommittedCount ?? 0,
    sprintCompletedCount: metrics.sprintCompletedCount ?? 0,
    sprintAddedCount: metrics.sprintAddedCount ?? 0,
    sprintRemovedCount: metrics.sprintRemovedCount ?? 0,
    sprintCompletionBasis: metrics.sprintCompletionBasis ?? null,
    sprintCompletionStale: metrics.sprintCompletionStale ?? false,
    sprintName: metrics.sprintName ?? null,
    reopenedCount: metrics.reopenedCount ?? 0,
    reopenedRate: metrics.reopenedRatePercent ?? metrics.reopenedRate ?? 0,
    completedCount: metrics.completedCount ?? 0,
    wip: metrics.inProgressCount ?? metrics.wip ?? 0,
    backlogAging: metrics.backlogAgingDays ?? metrics.backlogAging ?? 0,
    throughput: metrics.throughput ?? 0,
    flowSampleSize: hasFlowSample ? metrics.flowSampleSize : null,
    flowSampleWindowDays: hasFlowSample ? (metrics.flowSampleWindowDays ?? 30) : null,
    flowSampleMode: hasFlowSample ? (metrics.flowSampleMode ?? "empty") : "legacy",
    wipItems: metrics.wipItems ?? [],
  };
}

export async function fetchLatest(project) {
  try {
    const body = await request(`/latest?project=${encodeURIComponent(project)}`);
    return normalizeSnapshot(body.snapshot);
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

export async function fetchHistory(project) {
  const body = await request(`/history?project=${encodeURIComponent(project)}`);
  return (body.snapshots || []).map(normalizeSnapshot).filter(Boolean);
}

export async function fetchProfiles() {
  const body = await request("/profiles");
  return body.profiles || [];
}

export async function postSyncAll(profileIds) {
  return request("/sync-all", { method: "POST", body: JSON.stringify({ profileIds }) });
}

export async function validateProfile(profileId) {
  return request("/validate-profile", { method: "POST", body: JSON.stringify({ profileId }) });
}
