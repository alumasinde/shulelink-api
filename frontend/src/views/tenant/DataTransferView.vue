<script setup>
import { ref } from 'vue'
import { getApiError } from '../../api/client'
import { dataTransfer } from '../../api/dataTransfer'

const type = ref('school')
const file = ref(null)
const mode = ref('create')
const busy = ref(false)
const error = ref('')
const result = ref(null)

function selectFile(event) { file.value = event.target.files?.[0] || null; result.value = null; error.value = '' }
function download(blob, filename) { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url) }
async function run(action) {
  busy.value=true; error.value=''
  try { download(await action(), type.value === 'school' ? 'ShuleLink_School_Structure.xlsx' : 'ShuleLink_Students_Guardians.xlsx') }
  catch (e) { error.value=getApiError(e) } finally { busy.value=false }
}
async function template() {
  busy.value=true; error.value=''
  try { download(await (type.value === 'school' ? dataTransfer.template() : dataTransfer.studentsTemplate()), type.value === 'school' ? 'ShuleLink_School_Structure_Template.xlsx' : 'ShuleLink_Students_Guardians_Template.xlsx') }
  catch (e) { error.value=getApiError(e) } finally { busy.value=false }
}
async function exportData() { await run(type.value === 'school' ? dataTransfer.exportSchoolStructure : dataTransfer.exportStudents) }
async function importData() {
  if (!file.value) { error.value='Select an .xlsx file first.'; return }
  busy.value=true; error.value=''; result.value=null
  try { result.value=await (type.value === 'school' ? dataTransfer.importSchoolStructure(file.value,mode.value) : dataTransfer.importStudents(file.value,mode.value)) }
  catch (e) { error.value=getApiError(e) } finally { busy.value=false }
}
</script>

<template>
  <div class="page-wrap">
    <div class="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
      <div><span class="eyebrow">DATA MANAGEMENT</span><h1 class="h3 fw-bold mt-2 mb-1">Import & Export</h1><p class="text-muted mb-0">Use ShuleLink Excel workbooks for controlled bulk data operations.</p></div>
      <div class="d-flex gap-2"><button class="btn btn-outline-primary" :disabled="busy" @click="template"><i class="bi bi-file-earmark-arrow-down me-2"></i>Download Template</button><button class="btn btn-primary" :disabled="busy" @click="exportData"><i class="bi bi-download me-2"></i>Export Current Data</button></div>
    </div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div class="card border-0 shadow-sm mb-4"><div class="card-body p-3"><div class="row g-3"><div class="col-md-6"><label class="form-label fw-semibold">Data set</label><select v-model="type" class="form-select"><option value="school">School Structure</option><option value="students">Students & Guardians</option></select></div><div class="col-md-6"><label class="form-label fw-semibold">Import mode</label><select v-model="mode" class="form-select"><option value="create">Create New — reject duplicates</option><option value="upsert">Upsert — create missing and update matching records</option></select></div></div></div></div>
    <div class="row g-4">
      <div class="col-lg-7"><div class="card border-0 shadow-sm h-100"><div class="card-header bg-white border-0 p-4"><h2 class="h5 fw-bold mb-1">Import {{ type === 'school' ? 'School Structure' : 'Students & Guardians' }}</h2><p class="text-muted mb-0">Validation happens before the transaction is committed. Failed imports do not partially update the school.</p></div><div class="card-body p-4 border-top"><input class="form-control mb-2" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="selectFile"><div class="form-text mb-4">Maximum 10 MB. Use the official template or an existing ShuleLink export.</div><button class="btn btn-primary" :disabled="busy || !file" @click="importData"><span v-if="busy" class="spinner-border spinner-border-sm me-2"></span><i v-else class="bi bi-upload me-2"></i>{{ busy ? 'Processing…' : 'Import Workbook' }}</button></div></div></div>
      <div class="col-lg-5"><div class="card border-0 shadow-sm h-100"><div class="card-header bg-white border-0 p-4"><h2 class="h5 fw-bold mb-1">Import order</h2><p class="text-muted mb-0">Dependencies are resolved automatically.</p></div><div class="card-body p-4 border-top"><ol v-if="type === 'school'" class="mb-0"><li>Campuses</li><li>Academic Years & Terms</li><li>Departments</li><li>Class Levels & Streams</li><li>Subjects & Class Subjects</li><li>School Settings</li></ol><ol v-else class="mb-0"><li>Students</li><li>Guardians</li><li>Student ↔ Guardian links</li><li>Enrollments</li></ol><div class="alert alert-light border mt-4 mb-0 small">Imports never delete records. Upsert only changes matching records and creates missing ones.</div></div></div></div>
    </div>
    <div v-if="result" class="card border-0 shadow-sm mt-4"><div class="card-body p-4"><div v-if="result.valid" class="alert alert-success mb-0"><strong>Import completed.</strong> Created: {{ result.created }} · Updated: {{ result.updated }}</div><div v-else><div class="alert alert-danger"><strong>Import was not committed.</strong> {{ result.error_count }} error(s) found.</div><div class="table-responsive"><table class="table table-sm align-middle"><thead><tr><th>Sheet</th><th>Row</th><th>Error</th></tr></thead><tbody><tr v-for="(item,index) in result.errors" :key="index"><td>{{ item.sheet }}</td><td>{{ item.row ?? '—' }}</td><td>{{ item.message }}</td></tr></tbody></table></div></div></div></div>
  </div>
</template>
