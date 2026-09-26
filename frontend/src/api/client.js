const BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", params, body, signal } = {}) {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (Array.isArray(value)) value.forEach((v) => url.searchParams.append(key, v));
    else if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  const response = await fetch(url, {
    method,
    signal,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail || `Request failed (${response.status})`, response.status);
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  search: (q, { page = 1, size = 10, tags = [] } = {}, signal) =>
    request("/api/search", { params: { q, page, size, tags }, signal }),
  suggest: (q, signal) => request("/api/suggest", { params: { q }, signal }),
  analyzeText: (text, signal) => request("/api/analyze", { method: "POST", body: { text, top_k: 8 }, signal }),
  createDocument: (doc) => request("/api/documents", { method: "POST", body: doc }),
  bulkIndex: (documents) => request("/api/documents/bulk", { method: "POST", body: { documents } }),
  job: (id) => request(`/api/jobs/${id}`),
  listDocuments: (page = 1, size = 20) => request("/api/documents", { params: { page, size } }),
  deleteDocument: (id) => request(`/api/documents/${id}`, { method: "DELETE" }),
  stats: () => request("/api/stats"),
};
