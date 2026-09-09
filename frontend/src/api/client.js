import axios from "axios";

const host = window.location.hostname;
const isPlatformHost = ["admin.localhost", "admin.shulelink.co.ke", "localhost", "127.0.0.1"].includes(host);
const configuredApi = import.meta.env.VITE_API_URL?.replace(/\/$/, "");

// Development may use bearer tokens. Production is always cookie based so
// access and refresh credentials are not exposed to JavaScript storage.
export const COOKIE_AUTH_MODE = import.meta.env.PROD || import.meta.env.VITE_AUTH_COOKIE_MODE === "true";

function resolveApiBase() {
  if (host.endsWith(".localhost")) return `${window.location.protocol}//${host}:8000/api/v1`;
  if (host.endsWith(".shulelink.co.ke")) return `${window.location.protocol}//${host}/api/v1`;
  if (isPlatformHost) return `${window.location.protocol}//admin.localhost:8000/api/v1`;
  return configuredApi || `${window.location.protocol}//${host}:8000/api/v1`;
}

export const API_BASE_URL = resolveApiBase();

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
  withCredentials: COOKIE_AUTH_MODE,
});

const SAFE_METHODS = new Set(["get", "head", "options"]);
const PUBLIC_AUTH_PATHS = [
  "/auth/login",
  "/auth/platform/login",
  "/auth/refresh",
  "/auth/csrf",
  "/auth/activate",
  "/auth/password-reset/request",
  "/auth/password-reset/confirm",
  "/auth/mfa/verify",
];

function readCookie(name) {
  const encoded = `${name}=`;
  const item = document.cookie.split("; ").find((part) => part.startsWith(encoded));
  return item ? decodeURIComponent(item.slice(encoded.length)) : null;
}

function isPublicAuthRequest(url = "") {
  return PUBLIC_AUTH_PATHS.some((path) => url.includes(path));
}

let csrfPromise = null;

async function ensureCsrf() {
  if (!COOKIE_AUTH_MODE) return null;

  const existing = readCookie("__Host-shulelink_csrf");
  if (existing) return existing;

  csrfPromise ||= axios.get(`${API_BASE_URL}/auth/csrf`, {
    withCredentials: true,
    timeout: 15000,
  });

  try {
    await csrfPromise;
    return readCookie("__Host-shulelink_csrf");
  } finally {
    csrfPromise = null;
  }
}

api.interceptors.request.use(async (config) => {
  const method = (config.method || "get").toLowerCase();

  if (!COOKIE_AUTH_MODE) {
    const token = localStorage.getItem("shulelink_access_token");
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  } else if (!SAFE_METHODS.has(method)) {
    const csrf = await ensureCsrf();
    if (csrf) {
      config.headers = config.headers || {};
      config.headers["X-CSRF-Token"] = csrf;
    }
  }

  return config;
});

let refreshing = null;

async function refreshSession() {
  if (refreshing) return refreshing;

  refreshing = (async () => {
    if (COOKIE_AUTH_MODE) {
      const csrf = await ensureCsrf();
      return axios.post(
        `${API_BASE_URL}/auth/refresh`,
        {},
        {
          withCredentials: true,
          timeout: 15000,
          headers: csrf ? { "X-CSRF-Token": csrf } : {},
        },
      );
    }

    const refreshToken = localStorage.getItem("shulelink_refresh_token");
    if (!refreshToken) throw new Error("No refresh token available");

    return axios.post(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { timeout: 15000 },
    );
  })();

  try {
    const response = await refreshing;

    if (!COOKIE_AUTH_MODE) {
      const accessToken = response.data?.access_token;
      const refreshToken = response.data?.refresh_token;
      if (!accessToken || !refreshToken) throw new Error("Invalid refresh response");

      localStorage.setItem("shulelink_access_token", accessToken);
      localStorage.setItem("shulelink_refresh_token", refreshToken);
    }

    return response;
  } finally {
    refreshing = null;
  }
}

function clearClientSession() {
  if (!COOKIE_AUTH_MODE) {
    localStorage.removeItem("shulelink_access_token");
    localStorage.removeItem("shulelink_refresh_token");
  }
  localStorage.removeItem("shulelink_user");
  window.dispatchEvent(new Event("shulelink:logout"));
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;

    if (
      status !== 401 ||
      !original ||
      original._retry ||
      isPublicAuthRequest(original.url)
    ) {
      return Promise.reject(error);
    }

    original._retry = true;

    try {
      const response = await refreshSession();

      if (!COOKIE_AUTH_MODE) {
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${response.data.access_token}`;
      }

      return api(original);
    } catch (refreshError) {
      clearClientSession();
      return Promise.reject(refreshError);
    }
  },
);

export function getApiError(error, fallback = "Something went wrong. Please try again.") {
  const payload = error?.response?.data;
  const structured = payload?.error;
  if (structured?.message) return structured.message;
  if (Array.isArray(payload?.detail)) return payload.detail.map((item) => item.msg || String(item)).join(" ");
  return payload?.detail || payload?.message || error?.message || fallback;
}
