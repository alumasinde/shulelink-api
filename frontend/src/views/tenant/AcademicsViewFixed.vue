<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { teachers, assignments, rooms, periods, timetable } from '../../api/academics'
import { academicYears, terms, classes, streams, subjects, departments, classSubjects } from '../../api/schoolStructure'
import TeacherManagementPanel from './TeacherManagementPanel.vue'
import TeacherSubjectsPanel from './TeacherSubjectsPanel.vue'

const tab = ref('teachers')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')
const teacherSubjectsLoading = ref(false)
const teacherSubjects = ref([])
const data = ref({ teachers: [], assignments: [], rooms: [], periods: [], timetable: [], years: [], terms: [], classes: [], streams: [], subjects: [], departments: [], classSubjects: [] })

const teacherForm = ref({ teacher_number: '', first_name: '', middle_name: '', last_name: '', gender: 'unspecified', phone: '', email: '', department_id: null, status: 'active' })
const assignmentForm = ref({ teacher_id: null, academic_year_id: null, academic_term_id: null, class_level_id: null, stream_id: null, subject_id: null })
const roomForm = ref({ code: '', name: '', capacity: null, room_type: '', is_active: true })
const periodForm = ref({ code: '', name: '', start_time: '08:00', end_time: '08:40', is_break: false, sort_order: 1, is_active: true })
const entryForm = ref({ academic_year_id: null, academic_term_id: null, class_level_id: null, stream_id: null, subject_id: null, teacher_id: null, room_id: null, period_id: null, day_of_week: 1, is_double: false, notes: '' })
const generateForm = ref({ academic_year_id: null, academic_term_id: null, class_level_id: null, stream_id: null, lessons_per_week: 3, replace_existing: false })
const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

const assignmentTerms = computed(() => data.value.terms.filter(t => !assignmentForm.value.academic_year_id || String(t.academic_year_id) === String(assignmentForm.value.academic_year_id)))
const assignmentStreams = computed(() => data.value.streams.filter(s => !assignmentForm.value.class_level_id || String(s.class_level_id) === String(assignmentForm.value.class_level_id)))
const assignmentClassSubjects = computed(() => data.value.classSubjects.filter(cs => !assignmentForm.value.class_level_id || String(cs.class_level_id) === String(assignmentForm.value.class_level_id)))
const assignmentSubjects = computed(() => {
  const classSubjectsList = assignmentClassSubjects.value.map(cs => data.value.subjects.find(s => String(s.id) === String(cs.subject_id))).filter(Boolean)
  if (!assignmentForm.value.teacher_id) return []
  const allowed = new Set(teacherSubjects.value.map(s => String(s.id)))
  return classSubjectsList.filter(s => allowed.has(String(s.id)))
})
const entryStreams = computed(() => data.value.streams.filter(s => !entryForm.value.class_level_id || String(s.class_level_id) === String(entryForm.value.class_level_id)))
const entryClassSubjects = computed(() => data.value.classSubjects.filter(cs => !entryForm.value.class_level_id || String(cs.class_level_id) === String(entryForm.value.class_level_id)))
const entrySubjects = computed(() => entryClassSubjects.value.map(cs => data.value.subjects.find(s => String(s.id) === String(cs.subject_id))).filter(Boolean))
const activeTeachers = computed(() => data.value.teachers.filter(t => t.status === 'active'))
const assignmentReady = computed(() => Boolean(assignmentForm.value.teacher_id && assignmentForm.value.academic_year_id && assignmentForm.value.academic_term_id && assignmentForm.value.class_level_id && assignmentForm.value.subject_id))

function resetAssignmentDependentFields() {
  assignmentForm.value.academic_term_id = null
  assignmentForm.value.stream_id = null
  assignmentForm.value.subject_id = null
}
function resetAssignmentClassFields() {
  assignmentForm.value.stream_id = null
  assignmentForm.value.subject_id = null
}
function resetEntryDependentFields() {
  entryForm.value.academic_term_id = null
  entryForm.value.stream_id = null
  entryForm.value.subject_id = null
  entryForm.value.teacher_id = null
}
function resetEntryClassFields() {
  entryForm.value.stream_id = null
  entryForm.value.subject_id = null
  entryForm.value.teacher_id = null
}
watch(() => assignmentForm.value.academic_year_id, resetAssignmentDependentFields)
watch(() => assignmentForm.value.class_level_id, resetAssignmentClassFields)
watch(() => entryForm.value.academic_year_id, resetEntryDependentFields)
watch(() => entryForm.value.class_level_id, resetEntryClassFields)

watch(() => assignmentForm.value.teacher_id, async teacherId => {
  assignmentForm.value.subject_id = null
  teacherSubjects.value = []
  if (!teacherId) return
  teacherSubjectsLoading.value = true
  try {
    teacherSubjects.value = await teachers.subjects(teacherId)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to load subjects configured for the selected teacher'
  } finally {
    teacherSubjectsLoading.value = false
  }
})
watch(() => assignmentForm.value.subject_id, value => {
  if (value && !assignmentSubjects.value.some(s => String(s.id) === String(value))) assignmentForm.value.subject_id = null
})
watch(() => assignmentForm.value.stream_id, value => {
  if (value && !assignmentStreams.value.some(s => String(s.id) === String(value))) assignmentForm.value.stream_id = null
})
watch(() => assignmentForm.value.academic_term_id, value => {
  if (value && !assignmentTerms.value.some(t => String(t.id) === String(value))) assignmentForm.value.academic_term_id = null
})
watch(() => entryForm.value.subject_id, value => {
  if (value && !entrySubjects.value.some(s => String(s.id) === String(value))) entryForm.value.subject_id = null
})
watch(() => entryForm.value.stream_id, value => {
  if (value && !entryStreams.value.some(s => String(s.id) === String(value))) entryForm.value.stream_id = null
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [a,b,c,d,e,f,g,h,i,j,k,l] = await Promise.all([
      teachers.list(), assignments.list(), rooms.list(), periods.list(), timetable.list(),
      academicYears.list(), terms.list(), classes.list(), streams.list(), subjects.list(), departments.list(), classSubjects.list()
    ])
    data.value = { teachers: a, assignments: b, rooms: c, periods: d, timetable: e, years: f, terms: g, classes: h, streams: i, subjects: j, departments: k, classSubjects: l }
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to load academic data'
  } finally { loading.value = false }
}
async function run(action) {
  saving.value = true; error.value = ''; success.value = ''
  try { await action(); success.value = 'Saved successfully'; await load() }
  catch (e) { error.value = e?.response?.data?.detail || 'The operation failed. Check the selected records and try again.' }
  finally { saving.value = false }
}
function resetTeacher() { teacherForm.value = { teacher_number:'', first_name:'', middle_name:'', last_name:'', gender:'unspecified', phone:'', email:'', department_id:null, status:'active' } }
function resetAssignment() { assignmentForm.value = { teacher_id:null, academic_year_id:null, academic_term_id:null, class_level_id:null, stream_id:null, subject_id:null }; teacherSubjects.value=[] }
async function addTeacher() { await run(async () => { await teachers.create(teacherForm.value); resetTeacher() }) }
async function addAssignment() {
  if (!assignmentReady.value) { error.value = 'Select a teacher, academic year, term, class and a subject configured for that teacher and assigned to the class.'; return }
  const validSubject = assignmentSubjects.value.some(s => String(s.id) === String(assignmentForm.value.subject_id))
  if (!validSubject) { error.value = 'The selected subject is not configured for this teacher and class. Choose one of the available subjects.'; return }
  await run(async () => { await assignments.create({ ...assignmentForm.value }); resetAssignment() })
}
async function removeAssignment(id) { if (!confirm('Remove this teaching assignment?')) return; await run(async () => { await (await import('../../api/client')).api.delete(`/academics/assignments/${id}`) }) }
async function addRoom() { await run(async () => { await rooms.create(roomForm.value); roomForm.value={code:'',name:'',capacity:null,room_type:'',is_active:true} }) }
async function addPeriod() { await run(async () => { await periods.create(periodForm.value); periodForm.value={code:'',name:'',start_time:'08:00',end_time:'08:40',is_break:false,sort_order:data.value.periods.length+1,is_active:true} }) }
async function addEntry() { await run(async () => { await timetable.create(entryForm.value) }) }
async function removeEntry(id) { if (!confirm('Remove this timetable entry?')) return; await run(async () => { await timetable.remove(id) }) }
async function generate() { await run(async () => { const r=await timetable.generate(generateForm.value); success.value=`Generated ${r.created} lesson(s); ${r.skipped} could not be placed.` }) }
function teacherPanelRefresh() { load() }
onMounted(load)
</script>

<template>
<div class="container-fluid py-4">
  <div class="d-flex justify-content-between align-items-center mb-4"><div><h1 class="h3 mb-1">Academics</h1><p class="text-muted mb-0">Teachers, teaching assignments and timetable management</p></div><button class="btn btn-outline-secondary" :disabled="loading" @click="load">Refresh</button></div>
  <div v-if="error" class="alert alert-danger">{{ error }}</div><div v-if="success" class="alert alert-success">{{ success }}</div>
  <ul class="nav nav-tabs mb-4"><li v-for="x in [['teachers','Teachers'],['assignments','Assignments'],['timetable','Timetable'],['configuration','Configuration']]" :key="x[0]" class="nav-item"><button class="nav-link" :class="{active:tab===x[0]}" @click="tab=x[0]">{{x[1]}}</button></li></ul>

  <section v-if="tab==='teachers'" class="row g-4">
    <div class="col-xl-4"><div class="card"><div class="card-header fw-semibold">Add teacher</div><div class="card-body"><form @submit.prevent="addTeacher"><div class="row g-2"><div class="col-6"><label class="form-label">Teacher No.</label><input v-model.trim="teacherForm.teacher_number" class="form-control" required></div><div class="col-6"><label class="form-label">Gender</label><select v-model="teacherForm.gender" class="form-select"><option>unspecified</option><option>male</option><option>female</option><option>other</option></select></div><div class="col-6"><label class="form-label">First name</label><input v-model.trim="teacherForm.first_name" class="form-control" required></div><div class="col-6"><label class="form-label">Last name</label><input v-model.trim="teacherForm.last_name" class="form-control" required></div><div class="col-12"><label class="form-label">Middle name</label><input v-model.trim="teacherForm.middle_name" class="form-control"></div><div class="col-6"><label class="form-label">Phone</label><input v-model.trim="teacherForm.phone" class="form-control"></div><div class="col-6"><label class="form-label">Email</label><input v-model.trim="teacherForm.email" type="email" class="form-control"></div><div class="col-12"><label class="form-label">Department</label><select v-model="teacherForm.department_id" class="form-select"><option :value="null">None</option><option v-for="d in data.departments" :key="d.id" :value="d.id">{{d.name}}</option></select></div><div class="col-12"><button class="btn btn-primary w-100" :disabled="saving">Add teacher</button></div></div></form></div></div></div>
    <div class="col-xl-8"><TeacherManagementPanel :teachers="data.teachers" :departments="data.departments" @refresh="teacherPanelRefresh" /></div>
    <div class="col-12"><TeacherSubjectsPanel /></div>
  </section>

  <section v-else-if="tab==='assignments'"><div class="card mb-4"><div class="card-header fw-semibold">Teaching assignments</div><div class="card-body"><div class="alert alert-info py-2 mb-3">Choose a teacher first. Their configured subjects are then intersected with the subjects assigned to the selected class.</div><form class="row g-2 align-items-end" @submit.prevent="addAssignment"><div class="col-lg-3"><label class="form-label">Teacher</label><select v-model="assignmentForm.teacher_id" class="form-select" required><option :value="null">Select teacher</option><option v-for="t in activeTeachers" :key="t.id" :value="t.id">{{t.first_name}} {{t.last_name}} ({{t.teacher_number}})</option></select><div v-if="teacherSubjectsLoading" class="form-text">Loading teacher subjects…</div><div v-else-if="assignmentForm.teacher_id && !teacherSubjects.length" class="form-text text-danger">No subjects configured for this teacher. Configure them under Teachers first.</div></div><div class="col-lg-2"><label class="form-label">Academic year</label><select v-model="assignmentForm.academic_year_id" class="form-select" required><option :value="null">Select year</option><option v-for="y in data.years" :key="y.id" :value="y.id">{{y.name}}</option></select></div><div class="col-lg-2"><label class="form-label">Term</label><select v-model="assignmentForm.academic_term_id" class="form-select" :disabled="!assignmentForm.academic_year_id" required><option :value="null">Select term</option><option v-for="t in assignmentTerms" :key="t.id" :value="t.id">{{t.name}}</option></select></div><div class="col-lg-2"><label class="form-label">Class</label><select v-model="assignmentForm.class_level_id" class="form-select" required><option :value="null">Select class</option><option v-for="c in data.classes" :key="c.id" :value="c.id">{{c.name}}</option></select></div><div class="col-lg-2"><label class="form-label">Stream</label><select v-model="assignmentForm.stream_id" class="form-select" :disabled="!assignmentForm.class_level_id"><option :value="null">All streams</option><option v-for="s in assignmentStreams" :key="s.id" :value="s.id">{{s.name}}</option></select></div><div class="col-lg-3"><label class="form-label">Subject</label><select v-model="assignmentForm.subject_id" class="form-select" :disabled="!assignmentForm.teacher_id || !assignmentForm.class_level_id || teacherSubjectsLoading" required><option :value="null">{{teacherSubjectsLoading?'Loading teacher subjects…':assignmentForm.teacher_id?'Select eligible subject':'Select teacher first'}}</option><option v-for="s in assignmentSubjects" :key="s.id" :value="s.id">{{s.name}} ({{s.code}})</option></select><div v-if="assignmentForm.teacher_id && assignmentForm.class_level_id && !teacherSubjectsLoading && !assignmentSubjects.length" class="form-text text-danger">No teacher subjects match this class. Check Teacher Subjects and Class Subjects.</div></div><div class="col-lg-2"><button class="btn btn-primary w-100" :disabled="saving || teacherSubjectsLoading || !assignmentReady || !assignmentSubjects.length">Assign</button></div></form></div></div><div class="card"><div class="table-responsive"><table class="table table-hover mb-0"><thead><tr><th>Teacher</th><th>Year/Term</th><th>Class</th><th>Stream</th><th>Subject</th><th></th></tr></thead><tbody><tr v-for="a in data.assignments" :key="a.id"><td>{{a.teacher_name}}</td><td>{{a.academic_year_name}} / {{a.academic_term_name}}</td><td>{{a.class_name}}</td><td>{{a.stream_name||'All'}}</td><td>{{a.subject_name}}</td><td class="text-end"><button class="btn btn-sm btn-outline-danger" @click="removeAssignment(a.id)">Remove</button></td></tr><tr v-if="!data.assignments.length"><td colspan="6" class="text-center text-muted py-4">No assignments yet.</td></tr></tbody></table></div></div></section>

  <section v-else-if="tab==='timetable'"><div class="card mb-4"><div class="card-header fw-semibold">Generate timetable</div><div class="card-body"><form class="row g-2 align-items-end" @submit.prevent="generate"><div class="col-md-2"><label class="form-label">Year</label><select v-model="generateForm.academic_year_id" class="form-select" required><option :value="null">Select</option><option v-for="y in data.years" :key="y.id" :value="y.id">{{y.name}}</option></select></div><div class="col-md-2"><label class="form-label">Term</label><select v-model="generateForm.academic_term_id" class="form-select" required><option :value="null">Select</option><option v-for="t in data.terms.filter(x=>!generateForm.academic_year_id||String(x.academic_year_id)===String(generateForm.academic_year_id))" :key="t.id" :value="t.id">{{t.name}}</option></select></div><div class="col-md-2"><label class="form-label">Lessons/week</label><input v-model.number="generateForm.lessons_per_week" type="number" min="1" max="10" class="form-control"></div><div class="col-md-2 form-check ms-2 mb-2"><input v-model="generateForm.replace_existing" class="form-check-input" type="checkbox" id="replace"><label for="replace" class="form-check-label">Replace existing</label></div><div class="col-md-2"><button class="btn btn-primary w-100" :disabled="saving">Generate</button></div></form></div></div><div class="card"><div class="card-header fw-semibold">Timetable entries <span class="badge bg-secondary">{{data.timetable.length}}</span></div><div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead><tr><th>Day</th><th>Period</th><th>Class</th><th>Subject</th><th>Teacher</th><th>Room</th><th></th></tr></thead><tbody><tr v-for="e in data.timetable" :key="e.id"><td>{{days[e.day_of_week-1]}}</td><td>{{e.period_name}}</td><td>{{e.class_name}} <span v-if="e.stream_name">— {{e.stream_name}}</span></td><td>{{e.subject_name}}</td><td>{{e.teacher_name}}</td><td>{{e.room_name||'—'}}</td><td class="text-end"><button class="btn btn-sm btn-outline-danger" @click="removeEntry(e.id)">Remove</button></td></tr><tr v-if="!data.timetable.length"><td colspan="7" class="text-center text-muted py-4">No timetable entries yet.</td></tr></tbody></table></div></div></section>

  <section v-else class="row g-4"><div class="col-xl-6"><div class="card"><div class="card-header fw-semibold">Rooms</div><div class="card-body"><form class="row g-2 mb-3" @submit.prevent="addRoom"><div class="col-3"><input v-model.trim="roomForm.code" class="form-control" placeholder="Code" required></div><div class="col-4"><input v-model.trim="roomForm.name" class="form-control" placeholder="Name" required></div><div class="col-3"><input v-model.number="roomForm.capacity" type="number" min="1" class="form-control" placeholder="Capacity"></div><div class="col-2"><button class="btn btn-primary w-100">Add</button></div></form><table class="table table-sm"><tbody><tr v-for="r in data.rooms" :key="r.id"><td>{{r.code}}</td><td>{{r.name}}</td><td>{{r.capacity||'—'}}</td></tr></tbody></table></div></div></div><div class="col-xl-6"><div class="card"><div class="card-header fw-semibold">Periods</div><div class="card-body"><form class="row g-2 mb-3" @submit.prevent="addPeriod"><div class="col-3"><input v-model.trim="periodForm.code" class="form-control" placeholder="Code" required></div><div class="col-4"><input v-model.trim="periodForm.name" class="form-control" placeholder="Name" required></div><div class="col-2"><input v-model="periodForm.start_time" type="time" class="form-control" required></div><div class="col-2"><input v-model="periodForm.end_time" type="time" class="form-control" required></div><div class="col-1"><button class="btn btn-primary w-100">+</button></div></form><table class="table table-sm"><tbody><tr v-for="p in data.periods" :key="p.id"><td>{{p.sort_order}}</td><td>{{p.name}}</td><td>{{p.start_time}}–{{p.end_time}}</td><td><span v-if="p.is_break" class="badge bg-warning text-dark">Break</span></td></tr></tbody></table></div></div></div></section>
</div>
</template>
