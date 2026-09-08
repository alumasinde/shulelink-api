import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { login as loginRequest, logout as logoutRequest, me as meRequest } from "../api/auth";

const ACCESS_KEY = "shulelink_access_token";
const REFRESH_KEY = "shulelink_refresh_token";
const USER_KEY = "shulelink_user";

function readUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); } catch { return null; }
}

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref(localStorage.getItem(ACCESS_KEY));
  const refreshToken = ref(localStorage.getItem(REFRESH_KEY));
  const user = ref(readUser());
  const loading = ref(false);

  const isAuthenticated = computed(() => Boolean(accessToken.value && refreshToken.value));
  const isPlatform = computed(() => user.value?.user_type === "platform");

  function persistTokens(data) {
    accessToken.value = data.access_token;
    refreshToken.value = data.refresh_token;
    localStorage.setItem(ACCESS_KEY, data.access_token);
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
  }

  async function login(credentials, type) {
    loading.value = true;
    try {
      persistTokens(await loginRequest(credentials, type));
      user.value = await meRequest();
      localStorage.setItem(USER_KEY, JSON.stringify(user.value));
      return user.value;
    } finally { loading.value = false; }
  }

  async function hydrate() {
    if (!isAuthenticated.value) return null;
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
    try { if (refreshToken.value) await logoutRequest(refreshToken.value); } finally { clear(); }
  }

  function clear() {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  return { accessToken, refreshToken, user, loading, isAuthenticated, isPlatform, login, hydrate, logout, clear };
});
