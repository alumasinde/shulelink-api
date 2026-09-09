import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { COOKIE_AUTH_MODE } from "../api/client";
import { login as loginRequest, logout as logoutRequest, me as meRequest, verifyMfa as verifyMfaRequest } from "../api/auth";

const ACCESS_KEY = "shulelink_access_token";
const REFRESH_KEY = "shulelink_refresh_token";
const USER_KEY = "shulelink_user";
const AUTH_EVENT = "shulelink:logout";

function readUser() {
  try {
    const value = localStorage.getItem(USER_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

function persistUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  else localStorage.removeItem(USER_KEY);
}

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref(COOKIE_AUTH_MODE ? null : localStorage.getItem(ACCESS_KEY));
  const refreshToken = ref(COOKIE_AUTH_MODE ? null : localStorage.getItem(REFRESH_KEY));
  const user = ref(readUser());
  const loading = ref(false);

  const isAuthenticated = computed(() => COOKIE_AUTH_MODE ? Boolean(user.value) : Boolean(accessToken.value && refreshToken.value));
  const isPlatform = computed(() => user.value?.user_type === "platform");

  function persistTokens(data = {}) {
    if (COOKIE_AUTH_MODE) {
      accessToken.value = null;
      refreshToken.value = null;
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
      return;
    }

    if (!data.access_token || !data.refresh_token) {
      throw new Error("Authentication response is incomplete.");
    }

    accessToken.value = data.access_token;
    refreshToken.value = data.refresh_token;
    localStorage.setItem(ACCESS_KEY, data.access_token);
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
  }

  async function loadCurrentUser() {
    const currentUser = await meRequest();
    user.value = currentUser;
    persistUser(currentUser);
    return currentUser;
  }

  async function login(credentials, type) {
    loading.value = true;
    try {
      const result = await loginRequest(credentials, type);
      if (result.mfa_required) return result;
      persistTokens(result);
      return await loadCurrentUser();
    } finally {
      loading.value = false;
    }
  }

  async function completeMfa(challengeId, code) {
    loading.value = true;
    try {
      const result = await verifyMfaRequest(challengeId, code);
      persistTokens(result);
      return await loadCurrentUser();
    } finally {
      loading.value = false;
    }
  }

  async function hydrate() {
    try {
      return await loadCurrentUser();
    } catch {
      clear();
      return null;
    }
  }

  async function logout() {
    try {
      if (COOKIE_AUTH_MODE || refreshToken.value) await logoutRequest(refreshToken.value);
    } finally {
      clear();
    }
  }

  function clear() {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  // A logout in another browser tab must invalidate this tab's in-memory state.
  function handleExternalLogout() {
    clear();
  }

  window.addEventListener(AUTH_EVENT, handleExternalLogout);

  return {
    accessToken,
    refreshToken,
    user,
    loading,
    isAuthenticated,
    isPlatform,
    login,
    completeMfa,
    hydrate,
    logout,
    clear,
  };
});
