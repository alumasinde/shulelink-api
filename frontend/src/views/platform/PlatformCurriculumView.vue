<script setup>
import { computed, onMounted, ref } from 'vue'
import { curriculum } from '../../api/curriculum'
import { getApiError } from '../../api/client'

const templates = ref([])
const selected = ref(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const editor = ref('')
const form = ref({ name: '', description: '', country_code: 'KE', framework_code: 'kenya_cbc' })

const counts = computed(() => selected.value?.counts || {})
const isDraft = computed(() => selected.value?.status === 'draft')

async function load() {
  loading.value = true; error.value = ''
  try { templates.value = await curriculum.platform.list(); if (!selected.value && templates.value.length) await open(templates.value[0].id) }
  catch (e) { error.value = getApiError(e) }
  finally { loading.value = false }
}
async function open(id) {
  error.value = ''; notice.value = ''
  try {
    selected.value = await curriculum.platform.get(id)
    form.value = { name: selected.value.name, description: selected.value.description || '', country_code: selected.value.country_code || '', framework_code: selected.value.framework_code || '' }
    editor.value = JSON.stringify(selected.value.document, null, 2)
  } catch (e) { error.value = getApiError(e) }
}
function parseDocument() {
  try { return JSON.parse(editor.value) }
  catch { throw new Error('Curriculum document is not valid JSON.') }
}
async function save() {
  if (!selected.value || !isDraft.value) return
  saving.value = true; error.value = ''; notice.value = ''
  try { selected.value = await curriculum.platform.update(selected.value.id, { ...form.value, document: parseDocument() }); notice.value = 'Draft saved.'; await load() }
  catch (e) { error.value = e.message?.includes('valid JSON') ? e.message : getApiError(e) }
  finally { saving.value = false }
}
async function clone() {
  if (!selected.value) return
  saving.value = true; error.value = ''
  try { const copy = await curriculum.platform.clone(selected.value.id); notice.value = 'New draft version created.'; await load(); await open(copy.id) }
  catch (e) { error.value = getApiError(e) }
  finally { saving.value = false }
}
async function publish() {
  if (!selected.value) return
  saving.value = true; error.value = ''; notice.value = ''
  try { selected.value = await curriculum.platform.publish(selected.value.id); notice.value = 'Curriculum version published.'; await load(); await open(selected.value.id) }
  catch (e) { error.value = getApiError(e) }
  finally { saving.value = false }
}
async function archive() {
  if (!selected.value) return
  saving.value = true; error.value = ''
  try { await curriculum.platform.archive(selected.value.id); notice.value = 'Template archived.'; selected.value = null; await load() }
  catch (e) { error.value = getApiError(e) }
  finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <div class="page-wrap">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div><span class="eyebrow">PLATFORM · CURRICULUM</span><h1 class="h3 fw-bold mt-2 mb-1">Curriculum Management</h1><p class="text-muted mb-0">Version and publish curriculum templates that schools can select and configure.</p></div>
      <div class="d-flex gap-2"><button class="btn btn-outline-primary" @click="clone" :disabled="!selected || saving"><i class="bi bi-copy me-2"></i>New version</button><button v-if="isDraft" class="btn btn-primary" @click="publish" :disabled="saving"><i class="bi bi-check2-circle me-2"></i>Publish</button></div>
    </div>

    <div v-if="error" class="alert alert-danger border-0 shadow-sm">{{ error }}</div>
    <div v-if="notice" class="alert alert-success border-0 shadow-sm">{{ notice }}</div>

    <div v-if="loading" class="text-muted py-5">Loading curriculum catalog...</div>
    <div v-else class="row g-4">
      <div class="col-xl-4">
        <div class="card border-0 shadow-sm">
          <div class="card-header bg-white border-0 p-4"><div class="d-flex justify-content-between"><strong>Templates</strong><span class="badge text-bg-light border">{{ templates.length }}</span></div></div>
          <div class="list-group list-group-flush">
            <button v-for="item in templates" :key="item.id" class="list-group-item list-group-item-action p-3 text-start" :class="{ active: selected?.id === item.id }" @click="open(item.id)">
              <div class="d-flex justify-content-between gap-2"><strong>{{ item.name }}</strong><span class="badge" :class="item.status === 'published' ? 'text-bg-success' : 'text-bg-warning'">{{ item.status }}</span></div>
              <div class="small opacity-75 mt-1">{{ item.code }} · v{{ item.version_no }}</div>
              <div class="small mt-2">{{ item.counts.grades }} grades · {{ item.counts.subjects }} subjects · {{ item.counts.pathways }} pathways</div>
            </button>
          </div>
        </div>
      </div>

      <div class="col-xl-8">
        <div v-if="selected" class="card border-0 shadow-sm">
          <div class="card-body p-4">
            <div class="d-flex flex-wrap justify-content-between gap-3 mb-4">
              <div><span class="eyebrow">{{ selected.code }} · VERSION {{ selected.version_no }}</span><h2 class="h5 fw-bold mt-2 mb-1">{{ selected.name }}</h2><p class="text-muted mb-0">{{ selected.status === 'published' ? 'Published versions are immutable. Create a new version to change the curriculum.' : 'Draft version — safe to edit before publication.' }}</p></div>
              <button v-if="selected.status === 'published' && !selected.is_default" class="btn btn-outline-danger btn-sm align-self-start" @click="archive" :disabled="saving">Archive</button>
            </div>
            <div class="row g-2 mb-4">
              <div v-for="item in [['levels','Levels'],['grades','Grades'],['learning_areas','Learning areas'],['subjects','Subjects'],['pathways','Pathways'],['tracks','Tracks'],['combinations','Combinations']]" :key="item[0]" class="col-6 col-md-3"><div class="p-3 rounded border bg-light"><div class="small text-muted">{{ item[1] }}</div><strong>{{ counts[item[0]] || 0 }}</strong></div></div>
            </div>
            <fieldset :disabled="!isDraft || saving">
              <div class="row g-3 mb-4"><div class="col-md-6"><label class="form-label">Template name</label><input v-model="form.name" class="form-control"></div><div class="col-md-3"><label class="form-label">Country</label><input v-model="form.country_code" class="form-control"></div><div class="col-md-3"><label class="form-label">Framework code</label><input v-model="form.framework_code" class="form-control"></div><div class="col-12"><label class="form-label">Description</label><textarea v-model="form.description" rows="2" class="form-control"></textarea></div></div>
              <label class="form-label">Curriculum definition</label><textarea v-model="editor" rows="25" class="form-control font-monospace small"></textarea>
              <div class="form-text">The definition is versioned as one atomic template. It supports education levels, grades, learning areas, subjects, offerings, pathways, tracks and subject combinations.</div>
              <div class="d-flex justify-content-end mt-3"><button class="btn btn-primary" @click="save" :disabled="!isDraft || saving"><span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>Save draft</button></div>
            </fieldset>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
