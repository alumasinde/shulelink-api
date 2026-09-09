<script setup>
import { computed, ref, watch } from 'vue'
import { teachers as teacherApi } from '../../api/academics'
import { dataTransfer } from '../../api/dataTransfer'
import { getApiError } from '../../api/client'

const props = defineProps({ teachers: { type: Array, default: () => [] }, departments: { type: Array, default: () => [] } })
const emit = defineEmits(['refresh'])

const search = ref('')
const statusFilter = ref('all')
const selected = ref(new Set())
const modal = ref(null)
const busy = ref(false)
const error = ref('')
const success = ref('')
const departmentId = ref(null)
const employmentType = ref('')
const status = ref('')
const gender = ref('')
const departmentSubjects = ref([])
const subjectIds = ref([])

const filteredTeachers = computed(() => props.teachers.filter(t => {
  const q = search.value.trim().toLowerCase()
  const matchesSearch = !q || [t.teacher_number, t.first_name, t.middle_name, t.last_name, t.email, t.phone, t.department_name].some(v => String(v || '').toLowerCase().includes(q))
  return matchesSearch && (statusFilter.value === 'all' || t.status === statusFilter.value)
}))
const selectedTeachers = computed(() => props.teachers.filter(t => selected.value.has(String(t.id))))
const selectedCount = computed(() => selected.value.size)
const allVisibleSelected = computed(() => filteredTeachers.value.length > 0 && filteredTeachers.value.every(t => selected.value.has(String(t.id))))
const selectedDepartmentId = computed(() => {
  const ids = new Set(selectedTeachers.value.map(t => String(t.department_id || '')))
  return ids.size === 1 && !ids.has('') ? [...ids][0] : null
})
const selectedDepartmentName = computed(() => props.departments.find(d => String(d.id) === String(selectedDepartmentId.value))?.name || '')

function clearMessages() { error.value = ''; success.value = '' }
function toggle(id) { const key = String(id); const next = new Set(selected.value); next.has(key) ? next.delete(key) : next.add(key); selected.value = next }
function toggleAll() {
  const next = new Set(selected.value)
  if (allVisibleSelected.value) filteredTeachers.value.forEach(t => next.delete(String(t.id)))
  else filteredTeachers.value.forEach(t => next.add(String(t.id)))
  selected.value = next
}
function clearSelection() { selected.value = new Set() }
function openBulkEdit() { clearMessages(); departmentId.value = null; employmentType.value = ''; status.value = ''; gender.value = ''; modal.value = 'edit' }
async function openBulkSubjects() {
  clearMessages()
  if (!selectedDepartmentId.value) { error.value = 'Bulk subject assignment requires all selected teachers to have the same department.'; return }
  modal.value = 'subjects'; subjectIds.value = []
  busy.value = true
  try { departmentSubjects.value = await teacherApi.departmentSubjects(selectedDepartmentId.value) }
  catch (e) { error.value = getApiError(e); modal.value = null }
  finally { busy.value = false }
}
function closeModal() { if (!busy.value) modal.value = null }
async function saveBulkEdit() {
  const changes = {}
  if (departmentId.value) changes.department_id = departmentId.value
  if (employmentType.value.trim()) changes.employment_type = employmentType.value.trim()
  if (status.value) changes.status = status.value
  if (gender.value) changes.gender = gender.value
  if (!Object.keys(changes).length) { error.value = 'Choose at least one field to update.'; return }
  busy.value = true; clearMessages()
  try {
    const result = await teacherApi.bulkUpdate([...selected.value], changes)
    success.value = `${result.updated} teacher(s) updated successfully.`
    modal.value = null; clearSelection(); emit('refresh')
  } catch (e) { error.value = getApiError(e) }
  finally { busy.value = false }
}
function toggleSubject(id) {
  const key = String(id)
  subjectIds.value = subjectIds.value.includes(key) ? subjectIds.value.filter(x => x !== key) : subjectIds.value.length < 2 ? [...subjectIds.value, key] : subjectIds.value
}
async function saveBulkSubjects() {
  if (!subjectIds.value.length || subjectIds.value.length > 2) { error.value = 'Select one or two subjects.'; return }
  busy.value = true; clearMessages()
  try {
    const result = await teacherApi.bulkSubjects([...selected.value], subjectIds.value)
    success.value = `${result.teachers} teacher(s) updated with ${result.subjects} subject(s).`
    modal.value = null; clearSelection(); emit('refresh')
  } catch (e) { error.value = getApiError(e) }
  finally { busy.value = false }
}
function download(blob, filename) { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url) }
async function transfer(action, filename) {
  busy.value = true; clearMessages()
  try { download(await action(), filename); success.value = 'File ready.' }
  catch (e) { error.value = getApiError(e) }
  finally { busy.value = false }
}
async function importWorkbook(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.xlsx')) { error.value = 'Only .xlsx Excel files are supported.'; return }
  busy.value = true; clearMessages()
  try {
    const result = await dataTransfer.importTeachers(file, 'upsert')
    if (result.valid) { success.value = `Import completed. Created: ${result.created}; Updated: ${result.updated}; Subject assignments: ${result.subject_assignments}.`; emit('refresh') }
    else { error.value = `${result.error_count} validation error(s) found. See Import & Export for the full error report.` }
  } catch (e) { error.value = getApiError(e) }
  finally { busy.value = false }
}
watch(() => props.teachers.map(t => t.id).join(','), () => {
  const valid = new Set(props.teachers.map(t => String(t.id)))
  selected.value = new Set([...selected.value].filter(id => valid.has(id)))
})
</script>

<template>
  <div class="card">
    <div class="card-header">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div><strong>Teachers</strong> <span class="badge bg-secondary ms-1">{{ props.teachers.length }}</span><div class="small text-muted mt-1">Select teachers for bulk editing or subject assignment.</div></div>
        <div class="d-flex flex-wrap gap-2">
          <button class="btn btn-sm btn-outline-secondary" :disabled="busy" @click="transfer(dataTransfer.teachersTemplate, 'ShuleLink_Teachers_Subject_Assignments_Template.xlsx')"><i class="bi bi-file-earmark-arrow-down me-1"></i>Template</button>
          <button class="btn btn-sm btn-outline-primary" :disabled="busy" @click="transfer(dataTransfer.exportTeachers, 'ShuleLink_Teachers_Subject_Assignments_Export.xlsx')"><i class="bi bi-download me-1"></i>Export</button>
          <label class="btn btn-sm btn-outline-success mb-0" :class="{disabled: busy}"><i class="bi bi-upload me-1"></i>Import<input type="file" class="d-none" accept=".xlsx" :disabled="busy" @change="importWorkbook"></label>
        </div>
      </div>
    </div>
    <div class="card-body border-top pb-2">
      <div class="row g-2 align-items-center">
        <div class="col-lg-6"><input v-model="search" class="form-control" placeholder="Search teacher number, name, phone, email or department"></div>
        <div class="col-lg-3"><select v-model="statusFilter" class="form-select"><option value="all">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="on_leave">On leave</option><option value="terminated">Terminated</option></select></div>
        <div class="col-lg-3 text-lg-end"><button class="btn btn-sm btn-outline-secondary" :disabled="!selectedCount" @click="clearSelection">Clear selection</button></div>
      </div>
      <div v-if="selectedCount" class="alert alert-primary d-flex flex-wrap justify-content-between align-items-center gap-2 py-2 mt-3 mb-2">
        <div><strong>{{ selectedCount }}</strong> teacher(s) selected<span v-if="selectedDepartmentName"> · {{ selectedDepartmentName }}</span></div>
        <div class="d-flex gap-2"><button class="btn btn-sm btn-primary" @click="openBulkEdit">Bulk edit</button><button class="btn btn-sm btn-outline-primary" @click="openBulkSubjects">Assign subjects</button></div>
      </div>
    </div>
    <div class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead><tr><th style="width:42px"><input class="form-check-input" type="checkbox" :checked="allVisibleSelected" @change="toggleAll"></th><th>No.</th><th>Name</th><th>Department</th><th>Subjects</th><th>Contact</th><th>Status</th></tr></thead>
        <tbody>
          <tr v-for="t in filteredTeachers" :key="t.id" :class="{ 'table-primary': selected.has(String(t.id)) }">
            <td><input class="form-check-input" type="checkbox" :checked="selected.has(String(t.id))" @change="toggle(t.id)"></td>
            <td>{{ t.teacher_number }}</td>
            <td><strong>{{ t.first_name }} {{ t.middle_name || '' }} {{ t.last_name }}</strong></td>
            <td>{{ t.department_name || '—' }}</td>
            <td><span v-if="t.subjects?.length" class="small">{{ t.subjects.map(s => s.name).join(', ') }}</span><span v-else class="text-muted small">Not configured</span></td>
            <td>{{ t.phone || t.email || '—' }}</td>
            <td><span class="badge" :class="t.status === 'active' ? 'bg-success' : 'bg-secondary'">{{ t.status }}</span></td>
          </tr>
          <tr v-if="!filteredTeachers.length"><td colspan="7" class="text-center text-muted py-4">No teachers match the current filter.</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div v-if="modal" class="modal-backdrop-custom">
    <div class="card shadow-lg modal-card">
      <div class="card-header d-flex justify-content-between align-items-center"><strong>{{ modal === 'edit' ? 'Bulk edit teachers' : 'Bulk assign subjects' }}</strong><button class="btn-close" :disabled="busy" @click="closeModal"></button></div>
      <div class="card-body">
        <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
        <p class="text-muted small">{{ selectedCount }} teacher(s) selected. Changes are applied as one transaction.</p>
        <template v-if="modal === 'edit'">
          <label class="form-label">Department <span class="text-muted">(leave unchanged)</span></label><select v-model="departmentId" class="form-select mb-3"><option :value="null">Leave unchanged</option><option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option></select>
          <label class="form-label">Employment type</label><input v-model="employmentType" class="form-control mb-3" placeholder="Leave blank to keep current value">
          <div class="row g-3"><div class="col-6"><label class="form-label">Status</label><select v-model="status" class="form-select"><option value="">Leave unchanged</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="on_leave">On leave</option><option value="terminated">Terminated</option></select></div><div class="col-6"><label class="form-label">Gender</label><select v-model="gender" class="form-select"><option value="">Leave unchanged</option><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option><option value="unspecified">Unspecified</option></select></div></div>
        </template>
        <template v-else>
          <div class="alert alert-info py-2">Only subjects from <strong>{{ selectedDepartmentName }}</strong> are available. Select up to two.</div>
          <div class="row g-2"><div v-for="subject in departmentSubjects" :key="subject.id" class="col-md-6"><button type="button" class="btn w-100 text-start" :class="subjectIds.includes(String(subject.id)) ? 'btn-primary' : 'btn-outline-secondary'" :disabled="!subjectIds.includes(String(subject.id)) && subjectIds.length >= 2" @click="toggleSubject(subject.id)">{{ subject.name }} <small class="d-block opacity-75">{{ subject.code }}</small></button></div></div>
          <div v-if="!departmentSubjects.length" class="alert alert-warning mt-3 mb-0">No active subjects are configured for this department.</div>
        </template>
      </div>
      <div class="card-footer d-flex justify-content-end gap-2"><button class="btn btn-outline-secondary" :disabled="busy" @click="closeModal">Cancel</button><button v-if="modal === 'edit'" class="btn btn-primary" :disabled="busy" @click="saveBulkEdit">{{ busy ? 'Saving…' : 'Apply changes' }}</button><button v-else class="btn btn-primary" :disabled="busy || !subjectIds.length" @click="saveBulkSubjects">{{ busy ? 'Saving…' : 'Assign subjects' }}</button></div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop-custom { position: fixed; inset: 0; z-index: 1050; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; padding: 1rem; }
.modal-card { width: min(680px, 100%); max-height: 90vh; overflow: auto; }
</style>
