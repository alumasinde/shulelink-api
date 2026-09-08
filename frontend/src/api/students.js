import { api } from './client'

export const students = {
  list: async (params = {}) => (await api.get('/students', { params })).data,
  get: async (id) => (await api.get(`/students/${id}`)).data,
  create: async (payload) => (await api.post('/students', payload)).data,
  update: async (id, payload) => (await api.patch(`/students/${id}`, payload)).data,
  guardians: async (id) => (await api.get(`/students/${id}/guardians`)).data,
  linkGuardian: async (id, payload) => (await api.post(`/students/${id}/guardians`, payload)).data,
  unlinkGuardian: async (id, guardianId) => (await api.delete(`/students/${id}/guardians/${guardianId}`)).data,
  enrollments: async (id) => (await api.get(`/students/${id}/enrollments`)).data,
  enroll: async (id, payload) => (await api.post(`/students/${id}/enrollments`, payload)).data,
  updateEnrollment: async (id, enrollmentId, payload) => (await api.patch(`/students/${id}/enrollments/${enrollmentId}`, payload)).data,
  documents: async (id) => (await api.get(`/students/${id}/documents`)).data,
  uploadDocument: async (id, payload) => (await api.post(`/students/${id}/documents`, payload)).data,
  documentTypes: async () => (await api.get('/students/document-types')).data,
  createDocumentType: async (payload) => (await api.post('/students/document-types', payload)).data,
}

export const guardians = {
  list: async (params = {}) => (await api.get('/students/guardians', { params })).data,
  get: async (id) => (await api.get(`/students/guardians/${id}`)).data,
  create: async (payload) => (await api.post('/students/guardians', payload)).data,
  update: async (id, payload) => (await api.patch(`/students/guardians/${id}`, payload)).data,
}
