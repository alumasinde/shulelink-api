<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { teachers } from '../../api/academics'
import { departments } from '../../api/schoolStructure'

const loading=ref(false); const saving=ref(false); const error=ref(''); const success=ref('')
const teacherList=ref([]); const departmentList=ref([]); const departmentSubjects=ref([])
const teacherId=ref(null); const departmentId=ref(null); const selectedSubjects=ref([])

const selectedTeacher=computed(()=>teacherList.value.find(t=>String(t.id)===String(teacherId.value)))
const canSave=computed(()=>Boolean(teacherId.value && departmentId.value && selectedSubjects.value.length<=2))

async function load(){
  loading.value=true; error.value=''
  try {
    const [t,d]=await Promise.all([teachers.list({status:'active'}),departments.list()])
    teacherList.value=t; departmentList.value=d
  } catch(e){ error.value=e?.response?.data?.detail||'Failed to load teachers and departments' }
  finally{ loading.value=false }
}
async function loadDepartmentSubjects(){
  selectedSubjects.value=[]; departmentSubjects.value=[]
  if(!departmentId.value) return
  try { departmentSubjects.value=await teachers.departmentSubjects(departmentId.value) }
  catch(e){ error.value=e?.response?.data?.detail||'Failed to load department subjects' }
}
async function loadTeacher(){
  selectedSubjects.value=[]
  if(!teacherId.value) return
  const teacher=selectedTeacher.value
  if(teacher?.department_id){ departmentId.value=teacher.department_id; await loadDepartmentSubjects() }
  try { const current=await teachers.subjects(teacherId.value); selectedSubjects.value=current.map(s=>String(s.id)).slice(0,2) }
  catch(e){ error.value=e?.response?.data?.detail||'Failed to load teacher subjects' }
}
watch(departmentId,loadDepartmentSubjects)
watch(teacherId,loadTeacher)
function toggleSubject(id){
  id=String(id)
  if(selectedSubjects.value.includes(id)){ selectedSubjects.value=selectedSubjects.value.filter(x=>x!==id); return }
  if(selectedSubjects.value.length>=2){ error.value='A teacher can select a maximum of two subjects.'; return }
  error.value=''; selectedSubjects.value=[...selectedSubjects.value,id]
}
async function save(){
  if(!canSave.value) return
  saving.value=true; error.value=''; success.value=''
  try { await teachers.updateSubjects(teacherId.value,selectedSubjects.value); success.value='Teacher subjects saved successfully.' }
  catch(e){ error.value=e?.response?.data?.detail||'Failed to save teacher subjects' }
  finally{ saving.value=false }
}
onMounted(load)
</script>

<template>
<div class="container-fluid py-4">
  <div class="d-flex justify-content-between align-items-center mb-4">
    <div><h1 class="h3 mb-1">Teacher Subjects</h1><p class="text-muted mb-0">Assign one or two subjects to a teacher. Subjects are loaded from the teacher's department.</p></div>
    <button class="btn btn-outline-secondary" :disabled="loading" @click="load">Refresh</button>
  </div>
  <div v-if="error" class="alert alert-danger">{{error}}</div>
  <div v-if="success" class="alert alert-success">{{success}}</div>
  <div class="card">
    <div class="card-body">
      <div class="row g-3">
        <div class="col-md-4">
          <label class="form-label">Teacher</label>
          <select v-model="teacherId" class="form-select">
            <option :value="null">Select teacher</option>
            <option v-for="t in teacherList" :key="t.id" :value="t.id">{{t.first_name}} {{t.last_name}} ({{t.teacher_number}})</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label">Department</label>
          <select v-model="departmentId" class="form-select" :disabled="!teacherId">
            <option :value="null">Select department</option>
            <option v-for="d in departmentList" :key="d.id" :value="d.id">{{d.name}}</option>
          </select>
          <div class="form-text">Changing the department clears the selected subjects.</div>
        </div>
        <div class="col-md-4">
          <label class="form-label">Selected</label>
          <div class="form-control bg-light">{{selectedSubjects.length}} / 2 subjects</div>
        </div>
      </div>
      <hr class="my-4">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <div><h2 class="h6 mb-0">Department subjects</h2><small class="text-muted">Select up to two.</small></div>
      </div>
      <div v-if="teacherId && departmentId && !departmentSubjects.length" class="alert alert-warning">No active subjects are configured for this department.</div>
      <div v-else class="row g-2">
        <div v-for="subject in departmentSubjects" :key="subject.id" class="col-md-4 col-lg-3">
          <button type="button" class="btn w-100 text-start" :class="selectedSubjects.includes(String(subject.id)) ? 'btn-primary' : 'btn-outline-secondary'" :disabled="!selectedSubjects.includes(String(subject.id)) && selectedSubjects.length>=2" @click="toggleSubject(subject.id)">
            <i class="bi" :class="selectedSubjects.includes(String(subject.id)) ? 'bi-check-square' : 'bi-square'"></i>
            <span class="ms-2">{{subject.name}}</span>
            <small class="d-block ms-4 opacity-75">{{subject.code}}</small>
          </button>
        </div>
      </div>
      <div class="mt-4 text-end"><button class="btn btn-primary" :disabled="saving || !canSave" @click="save">{{saving?'Saving…':'Save subjects'}}</button></div>
    </div>
  </div>
</div>
</template>
