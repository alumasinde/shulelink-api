import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { COOKIE_AUTH_MODE } from "../api/client";
import { login as loginRequest, logout as logoutRequest, me as meRequest, verifyMfa as verifyMfaRequest } from "../api/auth";

const ACCESS_KEY = "shulelink_access_token";
const REFRESH_KEY = "shulelink_refresh_token";
const USER_KEY = "shulelink_user";

function readUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); } catch { return null; }
}

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref(COOKIE_AUTH_MODE ? null : localStorage.getItem(ACCESS_KEY));
  const refreshToken = ref(COOKIE_AUTH_MODE ? null : localStorage.getItem(REFRESH_KEY));
  const user = ref(readUser());
  const loading = ref(false);

  const isAuthenticated = computed(() => COOKIE_AUTH_MODE ? Boolean(user.value) : Boolean(accessToken.value && refreshToken.value));
  const isPlatform = computed(() => user.value?.user_type === "platform");

  function persistTokens(data) {
    if (COOKIE_AUTH_MODE) {
      accessToken.value = null;
      refreshToken.value = null;
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
      return;
    }
    accessToken.value = data.access_token;
    refreshToken.value = data.refresh_token;
    localStorage.setItem(ACCESS_KEY, data.access_token);
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
  }

  async function login(credentials, type) {
    loading.value = true;
    try {
      const result = await loginRequest(credentials, type);
      if (result.mfa_required) return result;
      persistTokens(result);
      user.value = await meRequest();
      localStorage.setItem(USER_KEY, JSON.stringify(user.value));
      return user.value;
    } finally { loading.value = false; }
  }

  async function completeMfa(challengeId, code) {
    loading.value = true;
    try {
      const result = await verifyMfaRequest(challengeId, code);
      persistTokens(result);
      user.value = await meRequest();
      localStorage.setItem(USER_KEY, JSON.stringify(user.value));
      return user.value;
    } finally { loading.value = false; }
  }

  async function hydrate() {
    try {
      user.value = await meRequest();
      localStorage.setItem(USER_KEY, JSON.stringify(user.value));
      return user.value;
    } catch {
      clear();
      return null;
    }
  }

  async function logout() {
    try { if (COOKIE_AUTH_MODE || refreshToken.value) await logoutRequest(refreshToken.value); } finally { clear(); }
  }

  function clear() {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  return { accessToken, refreshToken, user, loading, isAuthenticated, isPlatform, login, completeMfa, hydrate, logout, clear };
});
