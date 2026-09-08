import axios from "axios";

const host = window.location.hostname;
const isPlatformHost = host === "admin.localhost" || host === "admin.shulelink.co.ke" || host === "localhost" || host === "127.0.0.1";
const configuredApi = import.meta.env.VITE_API_URL?.replace(/\/$/, "");

function resolveApiBase() {
  // Local development is host-aware. Never send platform/tenant requests to
  // 127.0.0.1 because the backend uses the Host header to resolve tenancy.
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
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("shulelink_access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status !== 401 || original?._retry || !localStorage.getItem("shulelink_refresh_token")) {
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      refreshing ||= axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: localStorage.getItem("shulelink_refresh_token"),
      });
      const { data } = await refreshing;
      localStorage.setItem("shulelink_access_token", data.access_token);
      localStorage.setItem("shulelink_refresh_token", data.refresh_token);
      refreshing = null;
      original.headers.Authorization = `Bearer ${data.access_token}`;
      return api(original);
    } catch (refreshError) {
      refreshing = null;
      localStorage.removeItem("shulelink_access_token");
      localStorage.removeItem("shulelink_refresh_token");
      localStorage.removeItem("shulelink_user");
      window.dispatchEvent(new Event("shulelink:logout"));
      return Promise.reject(refreshError);
    }
  },
);

export function getApiError(error, fallback = "Something went wrong. Please try again.") {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || String(item)).join(" ");
  return detail || error?.response?.data?.message || error?.message || fallback;
}
