<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const user = computed(() => auth.user || {})
const role = computed(() => user.value.roles?.[0] || 'tenant_user')
const portal = computed(() => user.value.portal || 'school')

const portalMeta = {
  'school-admin': { title: 'School Administration Portal', subtitle: 'Manage your school operations and configuration.', icon: 'bi-building-gear', links: [{ label: 'School Structure', to: '/school/structure', icon: 'bi-diagram-3' }, { label: 'Students', to: '/school/students', icon: 'bi-people' }, { label: 'Guardians', to: '/school/guardians', icon: 'bi-person-hearts' }] },
  registrar: { title: 'Registrar Portal', subtitle: 'Manage admissions, students, guardians and school records.', icon: 'bi-person-vcard', links: [{ label: 'Students', to: '/school/students', icon: 'bi-people' }, { label: 'Guardians', to: '/school/guardians', icon: 'bi-person-hearts' }, { label: 'School Structure', to: '/school/structure', icon: 'bi-diagram-3' }] },
  finance: { title: 'Finance Portal', subtitle: 'Manage school finance workflows and financial information.', icon: 'bi-cash-stack', links: [] },
  teacher: { title: 'Teacher Portal', subtitle: 'Focus on your classes, learners and teaching workflows.', icon: 'bi-person-workspace', links: [{ label: 'My Students', to: '/school/students', icon: 'bi-people' }] },
  parent: { title: 'Parent Portal', subtitle: 'View your children, school information and family services.', icon: 'bi-people-fill', links: [] },
  student: { title: 'Student Portal', subtitle: 'Your personal learning and school workspace.', icon: 'bi-mortarboard-fill', links: [] },
  school: { title: 'School Portal', subtitle: 'Your ShuleLink school workspace.', icon: 'bi-building', links: [] },
}

const meta = computed(() => portalMeta[portal.value] || portalMeta.school)
</script>

<template>
  <div class="container-fluid py-4">
    <div class="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-4">
      <div>
        <div class="text-muted small text-uppercase fw-semibold mb-1">{{ role.replace('_', ' ') }}</div>
        <h1 class="h3 fw-bold mb-1">{{ meta.title }}</h1>
        <p class="text-muted mb-0">{{ meta.subtitle }}</p>
      </div>
      <div class="text-end">
        <div class="fw-semibold">{{ user.first_name }} {{ user.last_name }}</div>
        <div class="small text-muted">{{ user.email }}</div>
      </div>
    </div>

    <div class="alert alert-light border mb-4">
      <i class="bi" :class="meta.icon"></i>
      <span class="ms-2">Access is controlled by your assigned role and server-side permissions.</span>
    </div>

    <div class="row g-3">
      <div v-for="link in meta.links" :key="link.to" class="col-md-4 col-xl-3">
        <RouterLink :to="link.to" class="card h-100 text-decoration-none shadow-sm border-0 portal-card">
          <div class="card-body p-4">
            <i class="bi fs-3" :class="link.icon"></i>
            <h2 class="h6 fw-bold mt-3 mb-1">{{ link.label }}</h2>
            <span class="small text-muted">Open module</span>
          </div>
        </RouterLink>
      </div>
      <div v-if="!meta.links.length" class="col-12">
        <div class="card border-0 shadow-sm"><div class="card-body p-5 text-center">
          <i class="bi fs-1 text-muted" :class="meta.icon"></i>
          <h2 class="h5 mt-3">Portal ready</h2>
          <p class="text-muted mb-0">This portal's business modules will appear here as they are enabled for your role.</p>
        </div></div>
      </div>
    </div>
  </div>
</template>
