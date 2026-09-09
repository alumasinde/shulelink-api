import axios from "axios";

const host = window.location.hostname.toLowerCase();
const apiPath = import.meta.env.VITE_API_PATH?.trim();
const apiPort = import.meta.env.VITE_API_PORT?.trim();
const platformHost = import.meta.env.VITE_PLATFORM_HOST?.trim().toLowerCase();
const rootDomain = import.meta.env.VITE_ROOT_DOMAIN?.trim().toLowerCase();
const developmentDomain = import.meta.env.VITE_DEVELOPMENT_DOMAIN?.trim().toLowerCase();
const developmentHosts = (import.meta.env.VITE_DEVELOPMENT_HOSTS || "")
  .split(",")
  .map((value) => value.trim().toLowerCase())
  .filter(Boolean);
const configuredCookieMode = import.meta.env.VITE_AUTH_COOKIE_MODE;

if (!apiPath || !apiPath.startsWith("/")) {
  throw new Error("VITE_API_PATH is required and must start with '/'");
}
if (!platformHost || !rootDomain || !developmentDomain || !developmentHosts.length) {
  throw new Error(
    "VITE_PLATFORM_HOST, VITE_ROOT_DOMAIN, VITE_DEVELOPMENT_DOMAIN and VITE_DEVELOPMENT_HOSTS are required",
  );
}
if (configuredCookieMode !== "true" && configuredCookieMode !== "false") {
  throw new Error("VITE_AUTH_COOKIE_MODE must be explicitly set to true or false");
}

// Production is always cookie based. Bearer tokens are retained only for local
// development so production credentials are never exposed to JavaScript storage.
export const COOKIE_AUTH_MODE = import.meta.env.PROD || configuredCookieMode === "true";

function resolveApiBase() {
  const isLocalHost = developmentHosts.includes(host) || host.endsWith(`.${developmentDomain}`);
  const isProductionHost = host === platformHost || host.endsWith(`.${rootDomain}`);

  if (!isLocalHost && !isProductionHost) {
    throw new Error(`Unsupported ShuleLink host: ${host}`);
  }

  if (isLocalHost && !apiPort) {
    throw new Error("VITE_API_PORT is required for local development");
  }

  const protocol = isLocalHost ? "http:" : "https:";
  const port = isLocalHost ? `:${apiPort}` : "";
  return `${protocol}//${host}${port}${apiPath}`;
}

export const API_BASE_URL = resolveApiBase();

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: COOKIE_AUTH_MODE,
  headers: { Accept: "application/json" },
});

const SAFE_METHODS = new Set(["get", "head", "options"]);
const PUBLIC_AUTH_PATHS = new Set([
  "/auth/login",
  "/auth/platform/login",
  "/auth/refresh",
  "/auth/csrf",
  "/auth/activate",
  "/auth/password-reset/request",
  "/auth/password-reset/confirm",
  "/auth/mfa/verify",
]);

function normalizePath(url = "") {
  try {
    return new URL(url, API_BASE_URL).pathname.replace(/\/$/, "") || "/";
  } catch {
    return String(url).split("?")[0].replace(/\/$/, "") || "/";
  }
}

function isPublicAuthRequest(url = "") {
  return PUBLIC_AUTH_PATHS.has(normalizePath(url));
}

function readCookie(name) {
  const encoded = `${name}=`;
  const item = document.cookie.split("; ").find((part) => part.trim().startsWith(encoded));
  if (!item) return null;
  try {
    return decodeURIComponent(item.trim().slice(encoded.length));
  } catch {
    return null;
  }
}

let csrfPromise = null;

async function ensureCsrf() {
  if (!COOKIE_AUTH_MODE) return null;

  const existing = readCookie("__Host-shulelink_csrf");
  if (existing) return existing;

  csrfPromise ||= axios.get(`${API_BASE_URL}/auth/csrf`, {
    withCredentials: true,
    timeout: 15000,
    headers: { Accept: "application/json" },
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
  } else if (!SAFE_METHODS.has(method) && !isPublicAuthRequest(config.url)) {
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
      { timeout: 15000, headers: { Accept: "application/json" } },
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
  if (!error) return fallback;

  const status = error.response?.status;
  const payload = error.response?.data;
  const structured = payload?.error;

  if (structured?.message && typeof structured.message === "string") return structured.message;

  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail
      .map((item) => (typeof item?.msg === "string" ? item.msg : null))
      .filter(Boolean);
    if (messages.length) return messages.join(" ");
  }

  if (typeof payload?.detail === "string") return payload.detail;
  if (typeof payload?.message === "string") return payload.message;

  if (error.code === "ECONNABORTED" || error.code === "ERR_NETWORK") {
    return "The service is temporarily unavailable. Please check your connection and try again.";
  }

  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "The requested resource was not found.";
  if (status === 409) return "This operation conflicts with existing data.";
  if (status === 429) return "Too many requests. Please wait and try again.";
  if (status >= 500) return "The service encountered an error. Please try again shortly.";

  return fallback;
}
