<script setup>
import { computed, onMounted, ref } from "vue";
import { tenantContext } from "../../api/tenants";
import { campuses, academicYears, terms, classes, streams, subjects, departments } from "../../api/schoolStructure";
import { getApiError } from "../../api/client";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const context = ref(null);
const loading = ref(true);
const error = ref("");
const counts = ref({ campuses: 0, academicYears: 0, terms: 0, classes: 0, streams: 0, subjects: 0, departments: 0 });
const hostname = computed(() => window.location.hostname);
const firstName = computed(() => auth.user?.first_name || "there");
const currentYear = computed(() => {
  const years = counts.value.academicYearsData || [];
  return years.find((item) => item.is_current) || years[0] || null;
});
const canManageAccounts = computed(() => auth.user?.permissions?.includes("accounts.manage"));

const setupItems = computed(() => [
  { label: "Campus", count: counts.value.campuses, icon: "bi-building", to: "/school/structure" },
  { label: "Academic year", count: counts.value.academicYears, icon: "bi-calendar3", to: "/school/structure" },
  { label: "Classes", count: counts.value.classes, icon: "bi-collection", to: "/school/structure" },
  { label: "Subjects", count: counts.value.subjects, icon: "bi-book", to: "/school/structure" },
]);

const setupComplete = computed(() => setupItems.value.filter((item) => item.count > 0).length);
const setupPercent = computed(() => Math.round((setupComplete.value / setupItems.value.length) * 100));

async function loadDashboard() {
  loading.value = true;
  error.value = "";
  try {
    const [tenant, campusRows, yearRows, termRows, classRows, streamRows, subjectRows, departmentRows] = await Promise.all([
      tenantContext(),
      campuses.list(),
      academicYears.list(),
      terms.list(),
      classes.list(),
      streams.list(),
      subjects.list(),
      departments.list(),
    ]);
    context.value = tenant;
    counts.value = {
      campuses: campusRows.length,
      academicYears: yearRows.length,
      academicYearsData: yearRows,
      terms: termRows.length,
      classes: classRows.length,
      streams: streamRows.length,
      subjects: subjectRows.length,
      departments: departmentRows.length,
    };
  } catch (e) {
    error.value = getApiError(e);
  } finally {
    loading.value = false;
  }
}

onMounted(loadDashboard);
</script>

<template>
  <div class="dashboard-page">
    <div v-if="loading" class="dashboard-loading">
      <div class="spinner-border text-primary" role="status"></div>
      <span>Loading your school workspace...</span>
    </div>

    <template v-else>
      <section class="dashboard-heading">
        <div>
          <div class="eyebrow">SCHOOL DASHBOARD</div>
          <h1>Good day, {{ firstName }} <span class="wave">👋</span></h1>
          <p>Here's what's happening in your school workspace.</p>
        </div>
        <div class="heading-actions">
          <router-link to="/school/structure" class="btn btn-primary">
            <i class="bi bi-plus-lg me-2"></i>Configure school
          </router-link>
        </div>
      </section>

      <div v-if="error" class="alert alert-danger border-0 shadow-sm mb-4">
        <i class="bi bi-exclamation-circle me-2"></i>{{ error }}
      </div>

      <section class="welcome-banner mb-4">
        <div class="welcome-copy">
          <div class="banner-label"><i class="bi bi-building me-2"></i>YOUR SCHOOL</div>
          <h2>{{ context?.name || tenantLabel }}</h2>
          <p>Set up your school foundation once, then build students, academics, attendance and fees on top of it.</p>
          <router-link to="/school/structure" class="banner-link">Open School Structure <i class="bi bi-arrow-right ms-2"></i></router-link>
        </div>
        <div class="welcome-art"><i class="bi bi-mortarboard-fill"></i></div>
      </section>

      <section class="metric-grid mb-4">
        <div class="metric-card"><div class="metric-icon"><i class="bi bi-building"></i></div><div><span>Campuses</span><strong>{{ counts.campuses }}</strong><small>Configured</small></div></div>
        <div class="metric-card"><div class="metric-icon"><i class="bi bi-calendar3"></i></div><div><span>Academic Years</span><strong>{{ counts.academicYears }}</strong><small>{{ currentYear ? `Current: ${currentYear.name}` : "Not configured" }}</small></div></div>
        <div class="metric-card"><div class="metric-icon"><i class="bi bi-collection"></i></div><div><span>Classes</span><strong>{{ counts.classes }}</strong><small>{{ counts.streams }} streams</small></div></div>
        <div class="metric-card"><div class="metric-icon"><i class="bi bi-book"></i></div><div><span>Subjects</span><strong>{{ counts.subjects }}</strong><small>{{ counts.departments }} departments</small></div></div>
      </section>

      <div class="row g-4">
        <div class="col-xl-8">
          <section class="dashboard-card h-100">
            <div class="card-heading"><div><h2>School setup</h2><p>Complete the essentials before adding operational data.</p></div><span class="setup-badge">{{ setupPercent }}% ready</span></div>
            <div class="progress setup-progress mb-4"><div class="progress-bar" :style="{ width: `${setupPercent}%` }"></div></div>
            <div class="setup-list">
              <router-link v-for="item in setupItems" :key="item.label" :to="item.to" class="setup-row"><span class="setup-row-icon"><i class="bi" :class="item.icon"></i></span><span class="setup-row-copy"><strong>{{ item.label }}</strong><small>{{ item.count > 0 ? `${item.count} configured` : "Needs configuration" }}</small></span><span v-if="item.count > 0" class="setup-check"><i class="bi bi-check-circle-fill"></i></span><span v-else class="setup-next"><i class="bi bi-arrow-right"></i></span></router-link>
            </div>
          </section>
        </div>

        <div class="col-xl-4">
          <section class="dashboard-card h-100 quick-card">
            <div class="card-heading"><div><h2>Quick actions</h2><p>Common school tasks.</p></div></div>
            <div class="quick-actions">
              <router-link to="/school/structure" class="quick-action"><span><i class="bi bi-diagram-3"></i></span><div><strong>School Structure</strong><small>Campuses, classes & subjects</small></div><i class="bi bi-chevron-right"></i></router-link>
              <router-link v-if="canManageAccounts" to="/school/portal-accounts" class="quick-action"><span><i class="bi bi-person-badge"></i></span><div><strong>Portal Accounts</strong><small>Parents & student login access</small></div><i class="bi bi-chevron-right"></i></router-link>
              <div class="quick-action muted"><span><i class="bi bi-person-plus"></i></span><div><strong>Add students</strong><small>Available in the next module</small></div><i class="bi bi-lock"></i></div>
              <div class="quick-action muted"><span><i class="bi bi-calendar-check"></i></span><div><strong>Take attendance</strong><small>Available in the next module</small></div><i class="bi bi-lock"></i></div>
            </div>
          </section>
        </div>
      </div>

      <section class="dashboard-footer mt-4"><div><i class="bi bi-shield-check"></i><span><strong>Secure school workspace</strong><small>Your workspace is isolated to <code>{{ hostname }}</code>.</small></span></div><router-link to="/school/structure">Manage settings <i class="bi bi-arrow-right ms-1"></i></router-link></section>
    </template>
  </div>
</template>
