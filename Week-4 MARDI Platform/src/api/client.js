/**
 * Thin fetch wrapper around every FastAPI endpoint in backend/app/api.py.
 * Centralizing these calls here means components never construct URLs or
 * handle fetch/json boilerplate themselves.
 *
 * BASE resolves to:
 *   - "/api" in local dev (Vite's dev-server proxy in vite.config.js
 *     forwards this to http://127.0.0.1:8000)
 *   - VITE_API_BASE + "/api" when deployed as a static site separately
 *     from the backend (set VITE_API_BASE to the deployed backend's full
 *     URL, e.g. https://mardi-backend.onrender.com, at build time)
 */
const BASE = `${import.meta.env.VITE_API_BASE || ""}/api`;

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${options.method || "GET"} ${path} failed: ${res.status} ${body}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),

  analyzeRequest: (user_request) =>
    request("/requests/analyze", { method: "POST", body: JSON.stringify({ user_request }) }),

  startRun: (user_request, max_revisions = 2) =>
    request("/runs", { method: "POST", body: JSON.stringify({ user_request, max_revisions }) }),

  listRuns: () => request("/runs"),

  getStatus: (runId) => request(`/runs/${runId}/status`),
  getTasks: (runId) => request(`/runs/${runId}/tasks`),
  getEvidence: (runId) => request(`/runs/${runId}/evidence`),
  getTrace: (runId) => request(`/runs/${runId}/trace`),
  getReport: (runId) => request(`/runs/${runId}/report`),
  getState: (runId) => request(`/runs/${runId}/state`),
  getCheckpoint: (runId) => request(`/runs/${runId}/checkpoint`),

  resolveCheckpoint: (runId, body) =>
    request(`/runs/${runId}/checkpoint`, { method: "POST", body: JSON.stringify(body) }),
};
