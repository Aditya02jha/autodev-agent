// Centralized API client.
//
// Previously the base URL "http://localhost:8000" was hardcoded in three
// different view files. That's fine for a laptop demo but breaks the moment
// you deploy the frontend anywhere else. It's now a single constant, and
// overridable via a Vite env var (create autodev-ui/.env with
// VITE_API_URL=https://your-api.example.com) without touching any component.
export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch {
    // fetch() throws on network failure (server down, CORS, offline, etc.)
    // — surface something actionable instead of a cryptic "Failed to fetch".
    throw new ApiError(
      `Could not reach the AutoDev server at ${API_BASE}. Is it running?`,
      0,
    );
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(text || `Request failed (${res.status})`, res.status);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) =>
    request(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  del: (path) => request(path, { method: "DELETE" }),
};

export { ApiError };
