<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { teachers } from '../../api/academics'
import { departments } from '../../api/schoolStructure'

const loading=ref(false)
const saving=ref(false)
const error=ref('')
const success=ref('')
const teacherList=ref([])
const departmentList=ref([])
const departmentSubjects=ref([])
const teacherId=ref(null)
const selectedSubjects=ref([])

const selectedTeacher=computed(()=>teacherList.value.find(t=>String(t.id)===String(teacherId.value)))
const departmentName=computed(()=>selectedTeacher.value?.department_name || departmentList.value.find(d=>String(d.id)===String(selectedTeacher.value?.department_id))?.name || '')
const canSave=computed(()=>Boolean(teacherId.value && selectedTeacher.value?.department_id && selectedSubjects.value.length>=1 && selectedSubjects.value.length<=2))

async function load(){
  loading.value=true; error.value=''; success.value=''
  try { const [t,d]=await Promise.all([teachers.list({status:'active'}),departments.list()]); teacherList.value=t; departmentList.value=d }
  catch(e){ error.value=e?.response?.data?.detail||'Failed to load teachers and departments' }
  finally{ loading.value=false }
}
async function loadTeacher(){
  selectedSubjects.value=[]; departmentSubjects.value=[]; error.value=''; success.value=''
  const teacher=selectedTeacher.value
  if(!teacherId.value || !teacher) return
  if(!teacher.department_id){ error.value='This teacher has no department. Assign a department before selecting subjects.'; return }
  loading.value=true
  try {
    const [current,available]=await Promise.all([teachers.subjects(teacherId.value),teachers.departmentSubjects(teacher.department_id)])
    selectedSubjects.value=current.map(s=>String(s.id)).slice(0,2)
    departmentSubjects.value=available
  } catch(e){ error.value=e?.response?.data?.detail||'Failed to load teacher subjects' }
  finally{ loading.value=false }
}
watch(teacherId,loadTeacher)
function toggle(id){
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
<div class="card mb-4 border-primary-subtle">
  <div class="card-header d-flex justify-content-between align-items-center">
    <div><strong>Teacher subjects</strong><div class="small text-muted">Select one or two subjects from the teacher's department. This is the same subject configuration used by teaching assignments.</div></div>
    <span v-if="teacherId" class="badge bg-primary">{{selectedSubjects.length}} / 2</span>
  </div>
  <div class="card-body">
    <div v-if="error" class="alert alert-danger py-2">{{error}}</div>
    <div v-if="success" class="alert alert-success py-2">{{success}}</div>
    <div class="row g-3 align-items-end">
      <div class="col-lg-4"><label class="form-label">Teacher</label><select v-model="teacherId" class="form-select"><option :value="null">Select teacher</option><option v-for="t in teacherList" :key="t.id" :value="t.id">{{t.first_name}} {{t.last_name}} ({{t.teacher_number}})</option></select></div>
      <div class="col-lg-3"><label class="form-label">Department</label><input class="form-control bg-light" :value="departmentName || '—'" readonly></div>
      <div class="col-lg-5"><div v-if="teacherId && selectedTeacher?.department_id" class="small text-muted">Subjects are restricted to this department. Select at most two.</div><div v-else class="small text-muted">Choose a teacher to load their department subjects.</div></div>
    </div>
    <div v-if="teacherId && selectedTeacher?.department_id" class="mt-3">
      <div v-if="!departmentSubjects.length" class="alert alert-warning py-2 mb-0">No active subjects are configured for this department.</div>
      <div v-else class="row g-2">
        <div v-for="subject in departmentSubjects" :key="subject.id" class="col-md-4 col-xl-3"><button type="button" class="btn w-100 text-start" :class="selectedSubjects.includes(String(subject.id))?'btn-primary':'btn-outline-secondary'" :disabled="!selectedSubjects.includes(String(subject.id)) && selectedSubjects.length>=2" @click="toggle(subject.id)"><i class="bi me-2" :class="selectedSubjects.includes(String(subject.id))?'bi-check-square':'bi-square'"></i>{{subject.name}}<small class="d-block ms-4 opacity-75">{{subject.code}}</small></button></div>
      </div>
      <div class="d-flex justify-content-between align-items-center mt-3"><small class="text-muted">Selected: {{selectedSubjects.length}} / 2</small><button class="btn btn-primary" :disabled="saving || loading || !canSave" @click="save">{{saving?'Saving…':'Save subjects'}}</button></div>
    </div>
  </div>
</div>
</template>
