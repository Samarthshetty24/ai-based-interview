const API_BASE = window.location.origin.includes('127.0.0.1') || window.location.origin.includes('localhost')
  ? 'http://127.0.0.1:8000/api'
  : ${window.location.origin}/api;

const api = {
  getToken: () => localStorage.getItem('token'),
  setToken: (token) => localStorage.setItem('token', token),
  getUser: () => JSON.parse(localStorage.getItem('user') || '{}'),
  setUser: (user) => localStorage.setItem('user', JSON.stringify(user)),
  clear: () => localStorage.clear(),

  requireAuth: () => {
    const token = localStorage.getItem('token');
    if (!token) window.location.href = 'login.html';
  },

  request: async (endpoint, options = {}) => {
    const token = api.getToken();
    const headers = {};
    if (token) headers['Authorization'] = Bearer ;

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(${API_BASE}, {
      ...options,
      headers: { ...headers, ...options.headers }
    });

    if (res.status === 401) {
      api.clear();
      window.location.href = 'login.html';
      return;
    }

    let data;
    try {
      data = await res.json();
    } catch (e) {
      const text = await res.text();
      throw new Error(text || 'Server Error');
    }

    if (!res.ok) throw new Error(data.detail || 'API Request Failed');
    return data;
  }
};
