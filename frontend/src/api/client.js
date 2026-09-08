import axios from "axios";

const host = window.location.hostname;
const isPlatformHost = host === "admin.localhost" || host === "admin.shulelink.co.ke" || host === "localhost" || host === "127.0.0.1";
const configuredApi = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
export const COOKIE_AUTH_MODE = import.meta.env.VITE_AUTH_COOKIE_MODE === "true";

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

function readCookie(name) {
  const encoded = `${name}=`;
  const item = document.cookie.split("; ").find((part) => part.startsWith(encoded));
  return item ? decodeURIComponent(item.slice(encoded.length)) : null;
}

let csrfPromise = null;
async function ensureCsrf() {
  if (!COOKIE_AUTH_MODE) return null;
  let token = readCookie("__Host-shulelink_csrf");
  if (token) return token;
  csrfPromise ||= axios.get(`${API_BASE_URL}/auth/csrf`, { withCredentials: true });
  await csrfPromise;
  csrfPromise = null;
  return readCookie("__Host-shulelink_csrf");
}

api.interceptors.request.use(async (config) => {
  if (!COOKIE_AUTH_MODE) {
    const token = localStorage.getItem("shulelink_access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } else if (!["get", "head", "options"].includes((config.method || "get").toLowerCase())) {
    const csrf = await ensureCsrf();
    if (csrf) config.headers["X-CSRF-Token"] = csrf;
  }
  return config;
});

let refreshing = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const hasRefresh = COOKIE_AUTH_MODE || Boolean(localStorage.getItem("shulelink_refresh_token"));
    if (error.response?.status !== 401 || original?._retry || !hasRefresh || original?.url?.includes("/auth/refresh")) {
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      refreshing ||= COOKIE_AUTH_MODE
        ? axios.post(`${API_BASE_URL}/auth/refresh`, {}, { withCredentials: true, headers: { "X-CSRF-Token": await ensureCsrf() } })
        : axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: localStorage.getItem("shulelink_refresh_token") });
      const { data } = await refreshing;
      refreshing = null;
      if (!COOKIE_AUTH_MODE) {
        localStorage.setItem("shulelink_access_token", data.access_token);
        localStorage.setItem("shulelink_refresh_token", data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
      }
      return api(original);
    } catch (refreshError) {
      refreshing = null;
      if (!COOKIE_AUTH_MODE) {
        localStorage.removeItem("shulelink_access_token");
        localStorage.removeItem("shulelink_refresh_token");
      }
      localStorage.removeItem("shulelink_user");
      window.dispatchEvent(new Event("shulelink:logout"));
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
