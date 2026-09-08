<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { useAuthStore } from '../../stores/auth'
import TenantDashboard from './TenantDashboard.vue'

const auth = useAuthStore()
const portal = computed(() => auth.user?.portal || 'school')

const ParentDashboard = defineAsyncComponent(() => import('./ParentDashboardView.vue'))
const StudentDashboard = defineAsyncComponent(() => import('./StudentDashboardView.vue'))

const dashboardComponent = computed(() => {
  if (portal.value === 'parent') return ParentDashboard
  if (portal.value === 'student') return StudentDashboard
  return TenantDashboard
})
</script>

<template>
  <component :is="dashboardComponent" />
</template>
