<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { teachers, academicsConfiguration } from '../../api/academics'
import { departments, subjects } from '../../api/schoolStructure'

const loading=ref(false)
const saving=ref(false)
const error=ref('')
const success=ref('')
const teacherList=ref([])
const departmentList=ref([])
const subjectList=ref([])
const teacherId=ref(null)
const selectedSubjects=ref([])
const policy=ref({ maxSubjects: null, departmentMatching: false })

const selectedTeacher=computed(()=>teacherList.value.find(t=>String(t.id)===String(teacherId.value)))
const departmentName=computed(()=>selectedTeacher.value?.department_name || departmentList.value.find(d=>String(d.id)===String(selectedTeacher.value?.department_id))?.name || '')
const maxSubjects=computed(()=>policy.value.maxSubjects)
const canSave=computed(()=>Boolean(teacherId.value))

async function load(){
  loading.value=true; error.value=''; success.value=''
  try {
    const [t,d,s,c]=await Promise.all([teachers.list({status:'active'}),departments.list(),subjects.list(),academicsConfiguration()])
    teacherList.value=t; departmentList.value=d; subjectList.value=s
    policy.value={ maxSubjects: c.settings?.academic?.default_teacher_subject_limit ?? c.settings?.['academic.default_teacher_subject_limit'] ?? null, departmentMatching: Boolean(c.settings?.academic?.enforce_department_subject_matching ?? c.settings?.['academic.enforce_department_subject_matching']) }
  } catch(e){ error.value=e?.response?.data?.detail||'Failed to load teachers, departments and subjects' }
  finally{ loading.value=false }
}
async function loadTeacher(){
  selectedSubjects.value=[]; error.value=''; success.value=''
  if(!teacherId.value) return
  loading.value=true
  try { selectedSubjects.value=(await teachers.subjects(teacherId.value)).map(s=>String(s.id)) }
  catch(e){ error.value=e?.response?.data?.detail||'Failed to load teacher subjects' }
  finally{ loading.value=false }
}
watch(teacherId,loadTeacher)
function toggle(id){
  id=String(id)
  if(selectedSubjects.value.includes(id)){ selectedSubjects.value=selectedSubjects.value.filter(x=>x!==id); return }
  if(maxSubjects.value !== null && selectedSubjects.value.length>=maxSubjects.value){ error.value=`The platform policy currently allows at most ${maxSubjects.value} subject eligibilities for a teacher.`; return }
  error.value=''; selectedSubjects.value=[...selectedSubjects.value,id]
}
async function save(){
  if(!canSave.value) return
  saving.value=true; error.value=''; success.value=''
  try { await teachers.updateSubjects(teacherId.value,selectedSubjects.value); success.value='Teacher subject eligibility saved successfully.' }
  catch(e){ error.value=e?.response?.data?.detail||'Failed to save teacher subject eligibility' }
  finally{ saving.value=false }
}
onMounted(load)
</script>

<template>
<div class="card mb-4 border-primary-subtle">
  <div class="card-header d-flex justify-content-between align-items-center">
    <div><strong>Teacher subject eligibility</strong><div class="small text-muted">Eligibility is independent from department membership. A teacher may be eligible for any number of subjects unless the platform administrator configures a limit.</div></div>
    <span v-if="teacherId" class="badge bg-primary">{{selectedSubjects.length}}<span v-if="maxSubjects !== null"> / {{maxSubjects}}</span></span>
  </div>
  <div class="card-body">
    <div v-if="error" class="alert alert-danger py-2">{{error}}</div>
    <div v-if="success" class="alert alert-success py-2">{{success}}</div>
    <div class="row g-3 align-items-end">
      <div class="col-lg-4"><label class="form-label">Teacher</label><select v-model="teacherId" class="form-select"><option :value="null">Select teacher</option><option v-for="t in teacherList" :key="t.id" :value="t.id">{{t.first_name}} {{t.last_name}} ({{t.teacher_number}})</option></select></div>
      <div class="col-lg-3"><label class="form-label">Department</label><input class="form-control bg-light" :value="departmentName || 'Not assigned'" readonly></div>
      <div class="col-lg-5"><div class="small text-muted">{{policy.departmentMatching ? 'Department matching is enabled by platform policy.' : 'Department is organizational only; it does not restrict teacher subject eligibility.'}}</div></div>
    </div>
    <div v-if="teacherId" class="mt-3">
      <div v-if="!subjectList.length" class="alert alert-warning py-2 mb-0">No active subjects are configured for this school.</div>
      <div v-else class="row g-2">
        <div v-for="subject in subjectList" :key="subject.id" class="col-md-4 col-xl-3"><button type="button" class="btn w-100 text-start" :class="selectedSubjects.includes(String(subject.id))?'btn-primary':'btn-outline-secondary'" :disabled="!selectedSubjects.includes(String(subject.id)) && maxSubjects !== null && selectedSubjects.length>=maxSubjects" @click="toggle(subject.id)"><i class="bi me-2" :class="selectedSubjects.includes(String(subject.id))?'bi-check-square':'bi-square'"></i>{{subject.name}}<small class="d-block ms-4 opacity-75">{{subject.code}}</small></button></div>
      </div>
      <div class="d-flex justify-content-between align-items-center mt-3"><small class="text-muted">Selected: {{selectedSubjects.length}}{{maxSubjects !== null ? ` / ${maxSubjects}` : ' (unlimited)'}}</small><button class="btn btn-primary" :disabled="saving || loading || !canSave" @click="save">{{saving?'Saving…':'Save eligibility'}}</button></div>
    </div>
  </div>
</div>
</template>
