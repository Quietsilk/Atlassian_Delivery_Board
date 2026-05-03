const BASE = "http://localhost:5678";

export async function fetchLatest(project) {
  const res = await fetch(`${BASE}/latest?project=${encodeURIComponent(project)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("HTTP " + res.status);
  const body = await res.json();
  if (!body.ok) throw new Error(body.error || "Server error");
  return body.snapshot;
}

export async function fetchHistory(project) {
  const res = await fetch(`${BASE}/history?project=${encodeURIComponent(project)}`);
  if (!res.ok) return [];
  const body = await res.json();
  return body.snapshots || [];
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
