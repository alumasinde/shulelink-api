<script setup>
import { onMounted, ref } from "vue";
import { tenantContext } from "../../api/tenants";
import { getApiError } from "../../api/client";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const context = ref(null);
const loading = ref(true);
const error = ref("");

onMounted(async () => {
  try { context.value = await tenantContext(); } catch (e) { error.value = getApiError(e); }
  finally { loading.value = false; }
});
</script>

<template>
  <div class="page-wrap">
    <div v-if="loading" class="py-5 text-center"><span class="spinner-border"></span></div>
    <template v-else>
      <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
        <div><span class="eyebrow">SCHOOL PORTAL</span><h1 class="h3 fw-bold mt-2 mb-1">Welcome, {{ auth.user?.first_name }}</h1><p class="text-muted mb-0">Your school workspace is connected and ready.</p></div>
        <span class="badge rounded-pill bg-success-subtle text-success-emphasis px-3 py-2"><i class="bi bi-check-circle me-1"></i>Tenant context active</span>
      </div>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <div class="row g-3 mb-4">
        <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-building"></i></div><div><div class="text-muted small">School</div><div class="fw-bold">{{ context?.name || 'Connected' }}</div></div></div></div>
        <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-person-badge"></i></div><div><div class="text-muted small">Signed in as</div><div class="fw-bold">{{ auth.user?.email }}</div></div></div></div>
        <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-globe2"></i></div><div><div class="text-muted small">School host</div><div class="fw-bold">{{ window.location.hostname }}</div></div></div></div>
      </div>
      <div class="card border-0 shadow-sm"><div class="card-body p-4"><h2 class="h5 fw-bold">Phase 2 connection check</h2><p class="text-muted">This page confirms that the Vue client can authenticate, send the bearer token and resolve the current tenant from the school hostname.</p><div class="row g-3"><div class="col-sm-4"><div class="check-item"><i class="bi bi-check-circle-fill"></i><span>Authentication</span></div></div><div class="col-sm-4"><div class="check-item"><i class="bi bi-check-circle-fill"></i><span>Tenant routing</span></div></div><div class="col-sm-4"><div class="check-item"><i class="bi bi-check-circle-fill"></i><span>API connection</span></div></div></div></div></div>
    </template>
  </div>
</template>
