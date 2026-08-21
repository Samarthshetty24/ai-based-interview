const API_BASE = "http://127.0.0.1:8000/api";

const api = {
  getToken: () => localStorage.getItem("token"),
  setToken: (token) => localStorage.setItem("token", token),
  getUser: () => JSON.parse(localStorage.getItem("user") || "{}"),
  setUser: (user) => localStorage.setItem("user", JSON.stringify(user)),
  clear: () => localStorage.clear(),

  // Enforce auth on private pages (dashboard, interview, resume, report)
  requireAuth: () => {
    const token = localStorage.getItem("token");
    if (!token) {
      window.location.href = "login.html";
    }
  },

  request: async (endpoint, options = {}) => {
    const token = api.getToken();
    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: { ...headers, ...options.headers }
    });

    if (res.status === 401) {
      api.clear();
      window.location.href = "login.html";
      return;
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "API Request Failed");
    return data;
  }
};
