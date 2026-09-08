<script setup>
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const isPlatformHost = computed(() => ["admin.localhost", "admin.shulelink.co.ke", "localhost", "127.0.0.1"].includes(window.location.hostname));
const tenantLabel = computed(() => window.location.hostname.split(".")[0]);

onMounted(() => {
  window.addEventListener("shulelink:logout", () => auth.clear());
});

async function logout() {
  await auth.logout();
  router.push("/login");
}
</script>

<template>
  <div class="app-shell">
    <nav v-if="auth.isAuthenticated" class="navbar navbar-expand-lg bg-white border-bottom sticky-top">
      <div class="container-fluid px-4">
        <router-link class="navbar-brand fw-bold d-flex align-items-center gap-2" :to="auth.isPlatform ? '/platform' : '/school'">
          <span class="brand-mark">S</span><span>ShuleLink</span>
        </router-link>
        <div class="d-flex align-items-center gap-3">
          <div class="text-end d-none d-sm-block">
            <div class="small fw-semibold">{{ auth.user?.first_name }} {{ auth.user?.last_name }}</div>
            <div class="text-muted tiny">{{ isPlatformHost ? 'Platform Administration' : tenantLabel }}</div>
          </div>
          <button class="btn btn-light btn-sm" @click="logout"><i class="bi bi-box-arrow-right me-1"></i>Logout</button>
        </div>
      </div>
    </nav>
    <main :class="route.name === 'login' || route.name === 'home' ? '' : 'container-fluid px-4 py-4'">
      <router-view />
    </main>
  </div>
</template>
