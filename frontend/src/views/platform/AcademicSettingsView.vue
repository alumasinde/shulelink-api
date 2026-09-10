<script setup>
import { onMounted, ref } from 'vue'
import { listPlatformAcademicSettings, updatePlatformAcademicSetting } from '../../api/platformAcademicSettings'
import { getApiError } from '../../api/client'

const settings = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')

function displayValue(item) {
  if (item.value_type === 'json') return JSON.stringify(item.setting_value, null, 2)
  if (item.setting_value === null || item.setting_value === undefined) return ''
  return String(item.setting_value)
}

async function load() {
  loading.value = true; error.value = ''
  try { settings.value = (await listPlatformAcademicSettings()).map(x => ({ ...x, draft: displayValue(x) })) }
  catch (e) { error.value = getApiError(e) }
  finally { loading.value = false }
}

function parse(item) {
  if (item.value_type === 'integer') return Number(item.draft)
  if (item.value_type === 'boolean') return item.draft === 'true' || item.draft === '1'
  if (item.value_type === 'json') {
    try { return JSON.parse(item.draft) } catch { throw new Error(`Invalid JSON for ${item.setting_key}`) }
  }
  if (item.draft === 'null') return null
  return item.draft
}

async function save(item) {
  saving.value = true; error.value = ''; success.value = ''
  try {
    const updated = await updatePlatformAcademicSetting(item.id, { setting_value: parse(item), value_type: item.value_type })
    Object.assign(item, updated, { draft: displayValue(updated) })
    success.value = 'Platform academic defaults updated. Schools will receive the new defaults unless they override the setting locally.'
  } catch (e) { error.value = e instanceof Error ? e.message : getApiError(e) }
  finally { saving.value = false }
}

onMounted(load)
</script>

<template>
  <div class="page-wrap">
    <div class="d-flex justify-content-between align-items-end gap-3 mb-4">
      <div><span class="eyebrow">PLATFORM / ACADEMICS</span><h1 class="h3 fw-bold mt-2 mb-1">Academic defaults</h1><p class="text-muted mb-0">Configure platform-wide academic behaviour. Schools inherit these values and may override supported settings.</p></div>
      <button class="btn btn-outline-secondary" :disabled="loading" @click="load">Refresh</button>
    </div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>
    <div class="alert alert-info"><strong>Design rule:</strong> these are defaults, not hardcoded Kenyan education rules. Curriculum, grade names, subjects, teacher eligibility limits and timetable policies remain configurable.</div>
    <div class="card border-0 shadow-sm">
      <div class="card-body">
        <div v-if="loading" class="text-center py-5"><span class="spinner-border spinner-border-sm"></span></div>
        <div v-else class="vstack gap-4">
          <div v-for="item in settings" :key="item.id" class="border rounded-3 p-3">
            <div class="d-flex justify-content-between gap-3 mb-2"><div><div class="fw-semibold">{{ item.setting_key }}</div><div class="small text-muted">{{ item.description }}</div></div><span class="badge text-bg-light border">{{ item.value_type }}</span></div>
            <textarea v-if="item.value_type === 'json'" v-model="item.draft" class="form-control font-monospace" rows="5"></textarea>
            <select v-else-if="item.value_type === 'boolean'" v-model="item.draft" class="form-select"><option value="true">Enabled</option><option value="false">Disabled</option></select>
            <input v-else v-model="item.draft" class="form-control" :type="item.value_type === 'integer' ? 'number' : 'text'">
            <div class="d-flex justify-content-end mt-2"><button class="btn btn-primary btn-sm" :disabled="saving" @click="save(item)">Save default</button></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
