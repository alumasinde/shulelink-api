import { api } from './client'

const resource = (name) => ({
  list: async () => (await api.get(`/school-structure/${name}`)).data,
  create: async (payload) => (await api.post(`/school-structure/${name}`, payload)).data,
})

export const campuses = resource('campuses')
export const academicYears = resource('academic-years')
export const terms = resource('terms')
export const departments = resource('departments')
export const classes = resource('classes')
export const streams = resource('streams')
export const subjects = resource('subjects')

export const classSubjects = {
  list: async () => (await api.get('/school-structure/class-subjects')).data,
  create: async (payload) => (await api.post('/school-structure/class-subjects', payload)).data,
}
export const schoolSettings = {
  list: async () => (await api.get('/school-structure/settings')).data,
  update: async (key, payload) => (await api.put(`/school-structure/settings/${encodeURIComponent(key)}`, payload)).data,
}
