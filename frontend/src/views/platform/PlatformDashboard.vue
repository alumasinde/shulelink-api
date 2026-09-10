<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useAuthStore } from "../../stores/auth";
import { system } from "../../api/system";
import { getApiError } from "../../api/client";

const auth = useAuthStore();
const loadingHealth = ref(true);
const refreshing = ref(false);
const healthError = ref("");
const checkedAt = ref(null);
const backend = ref({ status: "checking" });
const database = ref({ status: "checking" });
const pool = ref(null);
let refreshTimer = null;

const greeting = computed(() => {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
});

const healthState = computed(() => {
  if (backend.value.status === "checking" || database.value.status === "checking") return "Checking";
  if (backend.value.status === "healthy" && database.value.status === "healthy") return "All systems operational";
  return "Attention required";
});

const healthBadgeClass = computed(() => {
  if (healthState.value === "All systems operational") return "health-badge healthy";
  if (healthState.value === "Checking") return "health-badge checking";
  return "health-badge degraded";
});

const poolSummary = computed(() => {
  if (!pool.value) return "Connection pool metrics unavailable";
  const active = pool.value.active ?? pool.value.in_use ?? pool.value.used ?? null;
  const size = pool.value.size ?? pool.value.total ?? pool.value.max_size ?? null;
  if (active !== null && size !== null) return `${active} active · ${size} total`;
  if (size !== null) return `${size} connections reported`;
  return "Pool connected";
});

function statusLabel(status) {
  if (status === "healthy") return "Healthy";
  if (status === "checking") return "Checking…";
  return "Unavailable";
}

async function loadHealth(showSpinner = true) {
  if (showSpinner) refreshing.value = true;
  loadingHealth.value = true;
  healthError.value = "";
  backend.value = { status: "checking" };
  database.value = { status: "checking" };
  pool.value = null;

  const [healthResult, readinessResult] = await Promise.allSettled([
    system.health(),
    system.readiness(),
  ]);

  if (healthResult.status === "fulfilled" && healthResult.value?.success) {
    backend.value = {
      status: "healthy",
      version: healthResult.value.data?.version || "",
      service: healthResult.value.data?.service || "ShuleLink API",
    };
  } else {
    backend.value = { status: "unavailable" };
  }

  if (readinessResult.status === "fulfilled" && readinessResult.value?.success) {
    const checks = readinessResult.value.data?.checks || {};
    database.value = { status: checks.database === "ok" ? "healthy" : "unavailable" };
    pool.value = checks.database_pool || null;
  } else {
    database.value = { status: "unavailable" };
  }

  if (backend.value.status !== "healthy" || database.value.status !== "healthy") {
    const sourceError = healthResult.status === "rejected" ? healthResult.reason : readinessResult.reason;
    healthError.value = getApiError(sourceError, "One or more system health checks could not be completed.");
  }

  checkedAt.value = new Date();
  loadingHealth.value = false;
  refreshing.value = false;
}

function formatCheckedAt(value) {
  if (!value) return "Not checked yet";
  return value.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

onMounted(() => {
  loadHealth(false);
  refreshTimer = window.setInterval(() => loadHealth(false), 60000);
});

onUnmounted(() => {
  if (refreshTimer) window.clearInterval(refreshTimer);
});
</script>

<template>
  <div class="page-wrap platform-dashboard">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div>
        <span class="eyebrow">PLATFORM</span>
        <h1 class="h3 fw-bold mt-2 mb-1">{{ greeting }}, {{ auth.user?.first_name }}</h1>
        <p class="text-muted mb-0">Manage ShuleLink schools, curriculum templates, academic defaults and platform access.</p>
      </div>
      <div class="d-flex gap-2 flex-wrap">
        <router-link to="/platform/curriculum" class="btn btn-primary"><i class="bi bi-journal-bookmark me-2"></i>Curriculum</router-link>
        <router-link to="/platform/academic-settings" class="btn btn-outline-primary"><i class="bi bi-sliders me-2"></i>Academic defaults</router-link>
        <router-link to="/platform/tenants" class="btn btn-outline-primary"><i class="bi bi-building me-2"></i>Manage schools</router-link>
      </div>
    </div>

    <div class="system-status-card mb-4">
      <div class="system-status-heading">
        <div>
          <span class="eyebrow">SYSTEM STATUS</span>
          <h2 class="h5 fw-bold mt-2 mb-1">Platform health</h2>
          <p class="text-muted mb-0">Live checks from the ShuleLink API and database readiness endpoint.</p>
        </div>
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <span :class="healthBadgeClass"><span class="health-dot"></span>{{ healthState }}</span>
          <button class="btn btn-sm btn-outline-primary" type="button" @click="loadHealth()" :disabled="refreshing">
            <span v-if="refreshing" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi bi-arrow-clockwise me-1"></i>Refresh
          </button>
        </div>
      </div>

      <div v-if="healthError" class="alert alert-warning mt-3 mb-0 py-2">{{ healthError }}</div>

      <div class="row g-3 mt-1">
        <div class="col-md-4">
          <div class="health-check">
            <div class="health-icon"><i class="bi bi-hdd-network"></i></div>
            <div class="flex-grow-1">
              <div class="small text-muted">Backend API</div>
              <strong>{{ statusLabel(backend.status) }}</strong>
              <div class="tiny text-muted mt-1">{{ backend.version ? `v${backend.version}` : "HTTP health endpoint" }}</div>
            </div>
            <span class="status-pill" :class="backend.status">{{ statusLabel(backend.status) }}</span>
          </div>
        </div>
        <div class="col-md-4">
          <div class="health-check">
            <div class="health-icon"><i class="bi bi-database-check"></i></div>
            <div class="flex-grow-1">
              <div class="small text-muted">Database</div>
              <strong>{{ statusLabel(database.status) }}</strong>
              <div class="tiny text-muted mt-1">Readiness + connection test</div>
            </div>
            <span class="status-pill" :class="database.status">{{ statusLabel(database.status) }}</span>
          </div>
        </div>
        <div class="col-md-4">
          <div class="health-check">
            <div class="health-icon"><i class="bi bi-diagram-3"></i></div>
            <div class="flex-grow-1">
              <div class="small text-muted">Database pool</div>
              <strong>{{ pool ? "Connected" : loadingHealth ? "Checking…" : "Unavailable" }}</strong>
              <div class="tiny text-muted mt-1">{{ poolSummary }}</div>
            </div>
            <span class="status-pill" :class="pool ? 'healthy' : loadingHealth ? 'checking' : 'unavailable'">{{ pool ? "Ready" : loadingHealth ? "Checking" : "N/A" }}</span>
          </div>
        </div>
      </div>

      <div class="system-status-footer">
        <span><i class="bi bi-clock me-1"></i>Last checked {{ formatCheckedAt(checkedAt) }}</span>
        <span><i class="bi bi-shield-check me-1"></i>Health checks are read-only</span>
      </div>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-buildings"></i></div><div><div class="text-muted small">Schools</div><div class="h4 mb-0 fw-bold">Manage</div><div class="tiny text-muted mt-1">Platform school directory</div></div></div></div>
      <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-journal-bookmark"></i></div><div><div class="text-muted small">Curriculum</div><div class="h4 mb-0 fw-bold">Versioned</div><div class="tiny text-muted mt-1">Central curriculum catalog</div></div></div></div>
      <div class="col-md-4"><div class="stat-card"><div class="icon-box"><i class="bi bi-sliders2"></i></div><div><div class="text-muted small">Academic defaults</div><div class="h4 mb-0 fw-bold">Configurable</div><div class="tiny text-muted mt-1">Platform-wide defaults</div></div></div></div>
    </div>

    <div class="card border-0 shadow-sm"><div class="card-body p-4"><h2 class="h5 fw-bold">Platform administrator</h2><p class="text-muted mb-3">Curriculum templates are maintained centrally, published as immutable versions, and explicitly selected by schools. School-level configuration can then customize local offerings without changing the platform catalog.</p><div class="d-flex gap-2 flex-wrap"><span class="badge text-bg-light border">{{ auth.user?.email }}</span><span class="badge text-bg-light border">Platform user</span><span class="badge text-bg-light border">{{ healthState }}</span></div></div></div>
  </div>
</template>

<style scoped>
.system-status-card { background: #fff; border: 1px solid #e8edf3; border-radius: 16px; padding: 22px; box-shadow: 0 4px 18px rgba(23,32,51,.04); }
.system-status-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.health-badge { display: inline-flex; align-items: center; gap: 7px; border-radius: 999px; padding: 7px 11px; font-size: .72rem; font-weight: 700; }
.health-badge.healthy { background: #edf8f1; color: #18794e; }
.health-badge.checking { background: #f3f5f8; color: #667085; }
.health-badge.degraded { background: #fff4e5; color: #9a6700; }
.health-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.health-check { min-height: 102px; border: 1px solid #edf1f5; border-radius: 12px; padding: 14px; display: flex; align-items: center; gap: 11px; }
.health-icon { width: 40px; height: 40px; flex: 0 0 40px; border-radius: 10px; background: #eef4ff; color: var(--sl-primary); display: flex; align-items: center; justify-content: center; }
.status-pill { border-radius: 999px; padding: 5px 8px; font-size: .62rem; font-weight: 700; }
.status-pill.healthy { background: #edf8f1; color: #18794e; }
.status-pill.checking { background: #f3f5f8; color: #667085; }
.status-pill.unavailable { background: #fff0ef; color: #b42318; }
.system-status-footer { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-top: 15px; padding-top: 13px; border-top: 1px solid #edf1f5; color: #8a94a3; font-size: .68rem; }
.platform-dashboard :deep(.stat-card) { min-height: 100px; }
@media (max-width: 768px) { .system-status-heading { flex-direction: column; } }
</style>
