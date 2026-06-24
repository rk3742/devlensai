const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: options.body instanceof FormData
  ? { "ngrok-skip-browser-warning": "true" }
  : { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true", ...(options.headers || {}) },
      ...options,
    });
  } catch (err) {
    throw new ApiError(
      `Couldn't reach the DevLens AI backend at ${API_BASE}. Is the backend server running?`,
      0
    );
  }

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const message = data?.detail || `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return data;
}

export const api = {
  health: () => request("/api/health"),

  listRepositories: () => request("/api/repositories"),
  getRepository: (id) => request(`/api/repositories/${id}`),
  deleteRepository: (id) => request(`/api/repositories/${id}`, { method: "DELETE" }),

  importGithub: (url) =>
    request("/api/repositories/import/github", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  importZip: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("/api/repositories/import/zip", { method: "POST", body: formData });
  },

  getStructure: (id) => request(`/api/repositories/${id}/structure`),
  getDiagram: (id) => request(`/api/repositories/${id}/diagram`),
  getFiles: (id) => request(`/api/repositories/${id}/files`),
  explainFile: (id, path) =>
    request(`/api/repositories/${id}/files/explain?path=${encodeURIComponent(path)}`),
  getOnboarding: (id) => request(`/api/repositories/${id}/onboarding`),

  getChatHistory: (id) => request(`/api/repositories/${id}/chat`),
  askQuestion: (id, question) =>
    request(`/api/repositories/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  getReadme: (id) => request(`/api/repositories/${id}/docs/readme`),
  getApiDocs: (id) => request(`/api/repositories/${id}/docs/api`),
  getInstallGuide: (id) => request(`/api/repositories/${id}/docs/install-guide`),

  getDeadCode: (id) => request(`/api/repositories/${id}/quality/dead-code`),
  getTechDebt: (id) => request(`/api/repositories/${id}/quality/tech-debt`),
  getQualitySummary: (id) => request(`/api/repositories/${id}/quality/summary`),

  investigateBug: (id, description) =>
    request(`/api/repositories/${id}/investigate`, {
      method: "POST",
      body: JSON.stringify({ description }),
    }),

  compareRepositories: (repoAId, repoBId) =>
    request("/api/compare", {
      method: "POST",
      body: JSON.stringify({ repo_a_id: repoAId, repo_b_id: repoBId }),
    }),
};

export { ApiError };
