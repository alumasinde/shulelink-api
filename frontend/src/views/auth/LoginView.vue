<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getApiError } from "../../api/client";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const identifier = ref("");
const password = ref("");
const error = ref("");
const showPassword = ref(false);
const isPlatform = computed(() => ["admin.localhost", "admin.shulelink.co.ke", "localhost", "127.0.0.1"].includes(window.location.hostname));

function portalPath(user) {
  if (user?.user_type === "platform") return "/platform";
  const paths = { "school-admin": "/school/portal", registrar: "/school/portal", finance: "/school/portal", teacher: "/school/portal", parent: "/school/portal", student: "/school/portal" };
  return paths[user?.portal] || "/school/portal";
}

async function submit() {
  error.value = "";
  try {
    await auth.login({ email: identifier.value.trim(), password: password.value }, isPlatform.value ? "platform" : "tenant");
    router.replace(route.query.redirect || portalPath(auth.user));
  } catch (err) { error.value = getApiError(err, "Unable to sign in. Check your credentials and try again."); }
}
</script>

<template>
  <div class="login-page">
    <div class="login-panel">
      <div class="login-brand"><span class="brand-mark">S</span><span>ShuleLink</span></div>
      <div class="mt-5 mb-4">
        <span class="eyebrow">{{ isPlatform ? 'PLATFORM' : 'SCHOOL PORTAL' }}</span>
        <h1 class="h3 fw-bold mt-2 mb-2">Welcome back</h1>
        <p class="text-muted mb-0">Sign in to continue to your ShuleLink workspace.</p>
      </div>

      <div v-if="error" class="alert alert-danger d-flex gap-2 align-items-start" role="alert">
        <i class="bi bi-exclamation-circle"></i><span>{{ error }}</span>
      </div>

      <form @submit.prevent="submit" novalidate>
        <label class="form-label">Email or login ID</label>
        <div class="input-group mb-3">
          <span class="input-group-text bg-white"><i class="bi bi-person"></i></span>
          <input v-model="identifier" class="form-control" type="text" autocomplete="username" required placeholder="you@example.com or student-ADM-2026-0001">
        </div>
        <label class="form-label">Password</label>
        <div class="input-group mb-4">
          <span class="input-group-text bg-white"><i class="bi bi-lock"></i></span>
          <input v-model="password" class="form-control" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" required placeholder="Enter your password">
          <button class="btn btn-outline-secondary" type="button" @click="showPassword = !showPassword"><i :class="showPassword ? 'bi bi-eye-slash' : 'bi bi-eye'"></i></button>
        </div>
        <button class="btn btn-primary w-100 py-2 fw-semibold" :disabled="auth.loading">
          <span v-if="auth.loading" class="spinner-border spinner-border-sm me-2"></span>
          {{ auth.loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
      <p class="small text-muted text-center mt-4 mb-0">Secure access to your ShuleLink account.</p>
    </div>
  </div>
</template>
