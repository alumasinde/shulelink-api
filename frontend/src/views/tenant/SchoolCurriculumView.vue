<script setup>
import { computed, onMounted, ref } from 'vue'
import { curriculum } from '../../api/curriculum'
import { getApiError } from '../../api/client'

const templates = ref([])
const config = ref(null)
const loading = ref(true)
const selecting = ref(false)
const error = ref('')
const notice = ref('')
const current = computed(() => config.value?.profile)

async function load() {
  loading.value = true; error.value = ''
  try { [templates.value, config.value] = await Promise.all([curriculum.school.templates(), curriculum.school.configuration()]) }
  catch (e) { error.value = getApiError(e) }
  finally { loading.value = false }
}
async function selectTemplate(id) {
  selecting.value = true; error.value = ''; notice.value = ''
  try { config.value = await curriculum.school.selectTemplate(id, true); notice.value = 'Curriculum template applied to this school. Your school can now configure its local offerings.' }
  catch (e) { error.value = getApiError(e) }
  finally { selecting.value = false }
}
onMounted(load)
</script>

<template>
  <div class="page-wrap">
    <div class="mb-4"><span class="eyebrow">SCHOOL · CURRICULUM</span><h1 class="h3 fw-bold mt-2 mb-1">Curriculum</h1><p class="text-muted mb-0">Select a platform curriculum, then configure the subjects and offerings your school actually provides.</p></div>
    <div v-if="error" class="alert alert-danger border-0 shadow-sm">{{ error }}</div>
    <div v-if="notice" class="alert alert-success border-0 shadow-sm">{{ notice }}</div>
    <div v-if="loading" class="text-muted py-5">Loading curriculum...</div>
    <template v-else>
      <section class="card border-0 shadow-sm mb-4"><div class="card-body p-4"><div class="d-flex flex-wrap justify-content-between gap-3"><div><div class="small text-muted">CURRENT TEMPLATE</div><h2 class="h5 fw-bold mt-1">{{ current?.template_code || 'Not selected' }}</h2><p class="text-muted mb-0">{{ current ? `Version ${current.template_version} · ${current.status}` : 'Choose a published curriculum template below.' }}</p></div><span v-if="current" class="badge text-bg-success align-self-start">Active</span></div></div></section>
      <div class="row g-4 mb-4">
        <div class="col-md-3"><div class="stat-card"><div><div class="text-muted small">Education levels</div><div class="h4 mb-0 fw-bold">{{ config.levels?.length || 0 }}</div></div></div></div>
        <div class="col-md-3"><div class="stat-card"><div><div class="text-muted small">Grades</div><div class="h4 mb-0 fw-bold">{{ config.grades?.length || 0 }}</div></div></div></div>
        <div class="col-md-3"><div class="stat-card"><div><div class="text-muted small">Subjects</div><div class="h4 mb-0 fw-bold">{{ config.subjects?.length || 0 }}</div></div></div></div>
        <div class="col-md-3"><div class="stat-card"><div><div class="text-muted small">Pathways</div><div class="h4 mb-0 fw-bold">{{ config.pathways?.length || 0 }}</div></div></div></div>
      </div>
      <div class="card border-0 shadow-sm"><div class="card-header bg-white p-4 border-0"><strong>Published platform templates</strong><p class="text-muted small mb-0 mt-1">Selecting a template creates a tenant-local snapshot. Platform changes do not silently rewrite your school's academic history.</p></div><div class="table-responsive"><table class="table align-middle mb-0"><thead><tr><th>Template</th><th>Version</th><th>Status</th><th>Grades</th><th>Subjects</th><th></th></tr></thead><tbody><tr v-for="item in templates" :key="item.id"><td><strong>{{ item.name }}</strong><div class="small text-muted">{{ item.code }}</div></td><td>v{{ item.version_no }}</td><td><span class="badge text-bg-success">{{ item.status }}</span></td><td>{{ item.counts.grades }}</td><td>{{ item.counts.subjects }}</td><td class="text-end"><button class="btn btn-sm" :class="current?.platform_template_id === item.id ? 'btn-outline-secondary' : 'btn-primary'" :disabled="selecting || current?.platform_template_id === item.id" @click="selectTemplate(item.id)">{{ current?.platform_template_id === item.id ? 'Selected' : 'Select' }}</button></td></tr><tr v-if="!templates.length"><td colspan="6" class="text-center text-muted py-4">No published curriculum templates are available.</td></tr></tbody></table></div></div>
    </template>
  </div>
</template>
