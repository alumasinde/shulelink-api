<script setup>
import { computed } from "vue";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const greeting = computed(() => {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
});
</script>

<template>
  <div class="page-wrap">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div><span class="eyebrow">PLATFORM</span><h1 class="h3 fw-bold mt-2 mb-1">{{ greeting }}, {{ auth.user?.first_name }}</h1><p class="text-muted mb-0">Manage ShuleLink schools, curriculum defaults and platform access.</p></div>
      <div class="d-flex gap-2"><router-link to="/platform/academic-settings" class="btn btn-outline-primary"><i class="bi bi-sliders me-2"></i>Academic defaults</router-link><router-link to="/platform/tenants" class="btn btn-primary"><i class="bi bi-building me-2"></i>Manage schools</router-link></div>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-buildings"></i></div><div><div class="text-muted small">Schools</div><div class="h4 mb-0 fw-bold">Manage</div></div></div></div>
      <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-sliders"></i></div><div><div class="text-muted small">Academic defaults</div><div class="h4 mb-0 fw-bold">Configurable</div></div></div></div>
      <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-database-check"></i></div><div><div class="text-muted small">Database model</div><div class="h4 mb-0 fw-bold">Hybrid</div></div></div></div>
    </div>
    <div class="card border-0 shadow-sm">
      <div class="card-body p-4"><h2 class="h5 fw-bold">Platform administrator</h2><p class="text-muted mb-3">Platform defaults are inherited by schools. School-level configuration can override them where appropriate, while curriculum and education structures remain data-driven.</p><div class="d-flex gap-2 flex-wrap"><span class="badge text-bg-light border">{{ auth.user?.email }}</span><span class="badge text-bg-light border">Platform user</span></div></div>
    </div>
  </div>
</template>
