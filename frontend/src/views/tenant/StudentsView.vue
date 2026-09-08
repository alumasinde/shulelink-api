<script setup>
import { computed, onMounted, ref } from 'vue'
import { getApiError } from '../../api/client'
import { students, guardians } from '../../api/students'
import { academicYears, classes, streams } from '../../api/schoolStructure'

const rows = ref([])
const selected = ref(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const search = ref('')
const status = ref('')
const showCreate = ref(false)
const showGuardian = ref(false)
const showEnrollment = ref(false)
const guardianRows = ref([])
const years = ref([])
const classRows = ref([])
const streamRows = ref([])

const emptyStudent = () => ({ admission_number:'', first_name:'', middle_name:'', last_name:'', date_of_birth:'', gender:'unspecified', nationality:'Kenyan', birth_certificate_number:'', admission_date:'', previous_school:'', photo_url:'', status:'active', medical_notes:'', emergency_notes:'' })
const form = ref(emptyStudent())
const guardianForm = ref({ guardian_id:'', relationship:'Parent', is_primary:true, is_emergency_contact:true, can_pick_up:true })
const enrollmentForm = ref({ academic_year_id:'', class_level_id:'', stream_id:'', enrollment_date:new Date().toISOString().slice(0,10), exit_date:'', status:'active', notes:'' })

const filtered = computed(() => rows.value)
const fullName = (s) => [s.first_name,s.middle_name,s.last_name].filter(Boolean).join(' ')
const flash = (message) => { notice.value=message; setTimeout(()=>notice.value='',3000) }

async function load() {
  loading.value=true; error.value=''
  try { rows.value=await students.list({ search: search.value || undefined, status: status.value || undefined }) }
  catch(e){ error.value=getApiError(e) }
  finally { loading.value=false }
}
async function loadOptions(){
  try { [years.value,classRows.value,streamRows.value,guardianRows.value]=await Promise.all([academicYears.list(),classes.list(),streams.list(),guardians.list()]) }
  catch(e){ error.value=getApiError(e) }
}
function newStudent(){ form.value=emptyStudent(); showCreate.value=true; error.value='' }
async function createStudent(){
  saving.value=true; error.value=''
  try { await students.create(form.value); showCreate.value=false; await load(); flash('Student admitted successfully.') }
  catch(e){ error.value=getApiError(e) }
  finally { saving.value=false }
}
async function openStudent(row){
  try { selected.value=await students.get(row.id); error.value='' }
  catch(e){ error.value=getApiError(e) }
}
function openLinkGuardian(){ guardianForm.value={guardian_id:'',relationship:'Parent',is_primary:true,is_emergency_contact:true,can_pick_up:true}; showGuardian.value=true }
async function linkGuardian(){
  saving.value=true
  try { await students.linkGuardian(selected.value.id, guardianForm.value); selected.value=await students.get(selected.value.id); showGuardian.value=false; flash('Guardian linked.') }
  catch(e){ error.value=getApiError(e) }
  finally{ saving.value=false }
}
function openEnrollment(){ enrollmentForm.value={academic_year_id:years.value.find(y=>y.is_current)?.id || years.value[0]?.id || '',class_level_id:'',stream_id:'',enrollment_date:new Date().toISOString().slice(0,10),exit_date:'',status:'active',notes:''}; showEnrollment.value=true }
const availableStreams = computed(()=>streamRows.value.filter(s=>!enrollmentForm.value.class_level_id || s.class_level_id===enrollmentForm.value.class_level_id))
async function enroll(){
  saving.value=true
  try { await students.enroll(selected.value.id,{...enrollmentForm.value,stream_id:enrollmentForm.value.stream_id||null,exit_date:enrollmentForm.value.exit_date||null}); selected.value=await students.get(selected.value.id); showEnrollment.value=false; flash('Enrollment saved.') }
  catch(e){ error.value=getApiError(e) }
  finally{ saving.value=false }
}
async function removeGuardian(g){
  if(!confirm(`Remove ${fullName(g.guardian)} from this student?`)) return
  try { await students.unlinkGuardian(selected.value.id,g.guardian_id); selected.value=await students.get(selected.value.id); flash('Guardian relationship removed.') }
  catch(e){ error.value=getApiError(e) }
}
onMounted(async()=>{ await Promise.all([load(),loadOptions()]) })
</script>

<template>
  <div class="students-page">
    <div class="page-title-row">
      <div><div class="eyebrow">STUDENT MANAGEMENT</div><h1>Students</h1><p>Manage admissions, guardians and enrollment history.</p></div>
      <button class="btn btn-primary" @click="newStudent"><i class="bi bi-person-plus me-2"></i>Add student</button>
    </div>

    <div v-if="notice" class="alert alert-success border-0 shadow-sm">{{ notice }}</div>
    <div v-if="error" class="alert alert-danger border-0 shadow-sm">{{ error }}</div>

    <section class="dashboard-card mb-4">
      <div class="student-toolbar">
        <div class="search-box"><i class="bi bi-search"></i><input v-model="search" @keyup.enter="load" placeholder="Search admission number or student name..." /></div>
        <select v-model="status" class="form-select" @change="load"><option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="graduated">Graduated</option><option value="transferred">Transferred</option><option value="withdrawn">Withdrawn</option></select>
        <button class="btn btn-light" @click="load"><i class="bi bi-arrow-clockwise"></i></button>
      </div>
    </section>

    <div class="row g-4">
      <div :class="selected ? 'col-xl-7' : 'col-12'">
        <section class="dashboard-card">
          <div class="card-heading"><div><h2>Student register</h2><p>{{ rows.length }} student{{ rows.length===1?'':'s' }} shown</p></div></div>
          <div v-if="loading" class="py-5 text-center"><span class="spinner-border text-primary"></span></div>
          <div v-else-if="!filtered.length" class="empty-state"><i class="bi bi-people"></i><h3>No students yet</h3><p>Start by admitting your first student. Records will appear here automatically.</p><button class="btn btn-primary" @click="newStudent">Add first student</button></div>
          <div v-else class="table-responsive"><table class="table align-middle mb-0"><thead><tr><th>Admission</th><th>Student</th><th>Gender</th><th>Status</th><th></th></tr></thead><tbody><tr v-for="row in filtered" :key="row.id" :class="{ 'table-active':selected?.id===row.id }"><td class="fw-semibold">{{ row.admission_number }}</td><td><button class="student-link" @click="openStudent(row)">{{ fullName(row) }}</button></td><td class="text-capitalize">{{ row.gender }}</td><td><span class="status-pill" :class="row.status">{{ row.status }}</span></td><td class="text-end"><button class="btn btn-sm btn-light" @click="openStudent(row)"><i class="bi bi-chevron-right"></i></button></td></tr></tbody></table></div>
        </section>
      </div>

      <div v-if="selected" class="col-xl-5">
        <section class="dashboard-card student-detail-card">
          <div class="detail-head"><div class="student-avatar">{{ selected.first_name?.[0] }}{{ selected.last_name?.[0] }}</div><div><div class="eyebrow">{{ selected.admission_number }}</div><h2>{{ fullName(selected) }}</h2><span class="status-pill" :class="selected.status">{{ selected.status }}</span></div><button class="btn btn-sm btn-light ms-auto" @click="selected=null"><i class="bi bi-x-lg"></i></button></div>
          <div class="detail-actions"><button class="btn btn-primary btn-sm" @click="openEnrollment"><i class="bi bi-mortarboard me-1"></i>Enroll</button><button class="btn btn-outline-primary btn-sm" @click="openLinkGuardian"><i class="bi bi-person-plus me-1"></i>Guardian</button></div>
          <div class="detail-section"><h3>Profile</h3><div class="detail-grid"><div><small>Date of birth</small><strong>{{ selected.date_of_birth || 'Not provided' }}</strong></div><div><small>Gender</small><strong class="text-capitalize">{{ selected.gender }}</strong></div><div><small>Admission date</small><strong>{{ selected.admission_date || 'Not provided' }}</strong></div><div><small>Nationality</small><strong>{{ selected.nationality || 'Not provided' }}</strong></div></div></div>
          <div class="detail-section"><div class="section-title"><h3>Guardians</h3><button class="btn btn-link btn-sm" @click="openLinkGuardian">Add</button></div><div v-if="!selected.guardians?.length" class="mini-empty">No guardians linked yet.</div><div v-for="g in selected.guardians" :key="g.id" class="related-row"><div class="mini-avatar">{{ g.guardian?.first_name?.[0] }}{{ g.guardian?.last_name?.[0] }}</div><div><strong>{{ fullName(g.guardian) }}</strong><small>{{ g.relationship }}<span v-if="g.is_primary"> · Primary</span></small></div><button class="btn btn-sm btn-light ms-auto" @click="removeGuardian(g)"><i class="bi bi-x"></i></button></div></div>
          <div class="detail-section"><div class="section-title"><h3>Enrollment history</h3><button class="btn btn-link btn-sm" @click="openEnrollment">Add</button></div><div v-if="!selected.enrollments?.length" class="mini-empty">No enrollment history yet.</div><div v-for="e in selected.enrollments" :key="e.id" class="history-row"><div><strong>{{ e.academic_year_name }}</strong><small>{{ e.class_name }}<span v-if="e.stream_name"> · {{ e.stream_name }}</span></small></div><span class="status-pill" :class="e.status">{{ e.status }}</span></div></div>
        </section>
      </div>
    </div>

    <div v-if="showCreate" class="modal-backdrop-custom"><div class="modal-card modal-wide"><div class="modal-head"><div><h2>Admit student</h2><p>Create the student's master profile.</p></div><button class="btn btn-light" @click="showCreate=false"><i class="bi bi-x-lg"></i></button></div><div class="form-section"><h3>Identity</h3><div class="row g-3"><div class="col-md-4"><label>Admission number *</label><input v-model="form.admission_number" class="form-control" /></div><div class="col-md-4"><label>First name *</label><input v-model="form.first_name" class="form-control" /></div><div class="col-md-4"><label>Last name *</label><input v-model="form.last_name" class="form-control" /></div><div class="col-md-6"><label>Middle name</label><input v-model="form.middle_name" class="form-control" /></div><div class="col-md-3"><label>Date of birth</label><input v-model="form.date_of_birth" type="date" class="form-control" /></div><div class="col-md-3"><label>Gender</label><select v-model="form.gender" class="form-select"><option value="unspecified">Unspecified</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option></select></div><div class="col-md-4"><label>Nationality</label><input v-model="form.nationality" class="form-control" /></div><div class="col-md-4"><label>Birth certificate no.</label><input v-model="form.birth_certificate_number" class="form-control" /></div><div class="col-md-4"><label>Admission date</label><input v-model="form.admission_date" type="date" class="form-control" /></div></div></div><div class="form-section"><h3>Background</h3><div class="row g-3"><div class="col-md-6"><label>Previous school</label><input v-model="form.previous_school" class="form-control" /></div><div class="col-md-6"><label>Photo URL</label><input v-model="form.photo_url" class="form-control" placeholder="Optional" /></div><div class="col-12"><label>Medical notes</label><textarea v-model="form.medical_notes" class="form-control" rows="2"></textarea></div><div class="col-12"><label>Emergency notes</label><textarea v-model="form.emergency_notes" class="form-control" rows="2"></textarea></div></div></div><div class="modal-actions"><button class="btn btn-light" @click="showCreate=false">Cancel</button><button class="btn btn-primary" :disabled="saving" @click="createStudent">{{ saving?'Saving...':'Admit student' }}</button></div></div></div>

    <div v-if="showGuardian" class="modal-backdrop-custom"><div class="modal-card"><div class="modal-head"><div><h2>Link guardian</h2><p>Connect an existing guardian to {{ fullName(selected) }}.</p></div><button class="btn btn-light" @click="showGuardian=false"><i class="bi bi-x-lg"></i></button></div><label>Guardian *</label><select v-model="guardianForm.guardian_id" class="form-select mb-3"><option value="">Select guardian</option><option v-for="g in guardianRows" :key="g.id" :value="g.id">{{ fullName(g) }}{{ g.phone ? ` · ${g.phone}` : '' }}</option></select><label>Relationship *</label><input v-model="guardianForm.relationship" class="form-control mb-3" /><div class="form-check mb-2"><input v-model="guardianForm.is_primary" class="form-check-input" type="checkbox" id="primary"><label for="primary">Primary guardian</label></div><div class="form-check mb-2"><input v-model="guardianForm.is_emergency_contact" class="form-check-input" type="checkbox" id="emergency"><label for="emergency">Emergency contact</label></div><div class="form-check mb-4"><input v-model="guardianForm.can_pick_up" class="form-check-input" type="checkbox" id="pickup"><label for="pickup">Can pick up student</label></div><div class="modal-actions"><button class="btn btn-light" @click="showGuardian=false">Cancel</button><button class="btn btn-primary" :disabled="saving || !guardianForm.guardian_id" @click="linkGuardian">Link guardian</button></div></div></div>

    <div v-if="showEnrollment" class="modal-backdrop-custom"><div class="modal-card"><div class="modal-head"><div><h2>Enroll student</h2><p>Keep an academic history for {{ fullName(selected) }}.</p></div><button class="btn btn-light" @click="showEnrollment=false"><i class="bi bi-x-lg"></i></button></div><label>Academic year *</label><select v-model="enrollmentForm.academic_year_id" class="form-select mb-3"><option value="">Select year</option><option v-for="y in years" :key="y.id" :value="y.id">{{ y.name }}</option></select><label>Class *</label><select v-model="enrollmentForm.class_level_id" class="form-select mb-3"><option value="">Select class</option><option v-for="c in classRows" :key="c.id" :value="c.id">{{ c.name }}</option></select><label>Stream</label><select v-model="enrollmentForm.stream_id" class="form-select mb-3"><option value="">No stream</option><option v-for="s in availableStreams" :key="s.id" :value="s.id">{{ s.name }}</option></select><div class="row g-3 mb-3"><div class="col-6"><label>Enrollment date *</label><input v-model="enrollmentForm.enrollment_date" type="date" class="form-control" /></div><div class="col-6"><label>Status</label><select v-model="enrollmentForm.status" class="form-select"><option value="active">Active</option><option value="completed">Completed</option><option value="withdrawn">Withdrawn</option></select></div></div><label>Notes</label><textarea v-model="enrollmentForm.notes" class="form-control mb-4" rows="2"></textarea><div class="modal-actions"><button class="btn btn-light" @click="showEnrollment=false">Cancel</button><button class="btn btn-primary" :disabled="saving || !enrollmentForm.academic_year_id || !enrollmentForm.class_level_id" @click="enroll">Save enrollment</button></div></div></div>
  </div>	emplate>
