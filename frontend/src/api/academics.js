import { api } from './client'

const resource = (path) => ({
  list: async (params = {}) => (await api.get(path, { params })).data,
  create: async (payload) => (await api.post(path, payload)).data,
})

export const teachers = {
  ...resource('/academics/teachers'),
  departmentSubjects: async (departmentId) => (await api.get(`/academics/departments/${departmentId}/subjects`)).data,
  subjects: async (teacherId) => (await api.get(`/academics/teachers/${teacherId}/subjects`)).data,
  updateSubjects: async (teacherId, subjectIds) => (await api.put(`/academics/teachers/${teacherId}/subjects`, { subject_ids: subjectIds })).data,
  bulkUpdate: async (teacherIds, changes) => (await api.post('/academics/teachers/bulk-update', { teacher_ids: teacherIds, ...changes })).data,
  bulkSubjects: async (teacherIds, subjectIds) => (await api.put('/academics/teachers/bulk-subjects', { teacher_ids: teacherIds, subject_ids: subjectIds })).data,
}
export const assignments = resource('/academics/assignments')
export const rooms = { ...resource('/academics/timetable/rooms'), update: async (id,payload)=>(await api.put(`/academics/timetable/rooms/${id}`,payload)).data }
export const periods = { ...resource('/academics/timetable/periods'), update: async (id,payload)=>(await api.put(`/academics/timetable/periods/${id}`,payload)).data }
export const timetable = {
  list: async (params={}) => (await api.get('/academics/timetable',{params})).data,
  create: async (payload) => (await api.post('/academics/timetable',payload)).data,
  remove: async (id) => (await api.delete(`/academics/timetable/${id}`)).data,
  generate: async (payload) => (await api.post('/academics/timetable/generate',payload)).data,
}
