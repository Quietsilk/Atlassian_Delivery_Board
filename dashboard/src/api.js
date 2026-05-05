const BASE = "http://localhost:5678";

/**
 * Safely parse analysis — backend may return:
 *  - already-parsed object { summary, risks, actions }
 *  - JSON string (raw OpenAI output)
 *  - null / undefined
 */
function parseAnalysis(raw) {
  if (!raw) return null;
  if (typeof raw === "object" && raw.summary) return raw;
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.summary) return parsed;
    } catch {}
  }
  return null;
}

function normalizeSnapshot(snapshot) {
  if (!snapshot) return null;
  const metrics = snapshot.metrics || snapshot;
  const rawAnalysis = metrics.analysis ?? snapshot.analysis ?? null;
  return {
    timestamp:       snapshot.timestamp || null,
    cycleTime:       metrics.cycleTimeP50        ?? metrics.cycleTimeDays    ?? metrics.cycleTime    ?? 0,
    cycleTimeP85:    metrics.cycleTimeP85         ?? 0,
    timeToMarket:    metrics.timeToMarketP50      ?? metrics.timeToMarketDays ?? metrics.timeToMarket ?? 0,
    timeToMarketP85: metrics.timeToMarketP85      ?? 0,
    flowEfficiency:  metrics.flowEfficiencyPercent ?? metrics.flowEfficiency  ?? 0,
    reopened:        metrics.reopenedCount         ?? metrics.reopened        ?? 0,
    completedCount:  metrics.completedCount        ?? 0,
    wip:             metrics.inProgressCount       ?? metrics.wip             ?? 0,
    backlogAging:    metrics.backlogAgingDays       ?? metrics.backlogAging    ?? 0,
    throughput:      metrics.throughput            ?? 0,
    wipItems:        metrics.wipItems              ?? [],
    analysis:        parseAnalysis(rawAnalysis),
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

/**
 * POST /sync — source-aware.
 *
 * @param {string} project  - project key / label
 * @param {string} source   - "jira" | "linear" | "asana" | "clickup"
 * @param {object} creds    - saved credentials for the active source (from useCredentials)
 * @param {string} [jql]    - optional JQL override (Jira only)
 */
export async function postSync({ project, source = "jira", creds = {}, jql }) {
  const body = { project, source };

  if (source === "jira") {
    body.baseUrl  = creds.baseUrl;
    body.email    = creds.email;
    body.apiToken = creds.apiToken;
    // Auto-generate JQL from project label if not provided
    body.jql      = jql || `project = "${project.toUpperCase().replace(/\s+/g, "-")}" ORDER BY updated DESC`;
  } else if (source === "linear") {
    body.apiKey = creds.apiKey;
    body.teamId = creds.teamId || "";
  } else if (source === "asana") {
    body.accessToken = creds.accessToken;
    body.projectGid  = creds.workspaceId; // field id in Sidebar is workspaceId
  } else if (source === "clickup") {
    body.apiKey = creds.apiToken; // Sidebar field id is apiToken, backend expects apiKey
    body.teamId = creds.teamId   || "";
    body.listId = creds.listId   || "";
  }

  const res = await fetch(`${BASE}/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Sync failed: " + res.status);
  return res.json();
}
