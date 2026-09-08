import { api } from './client'

export const portalAccounts = {
  guardian: async (id) => (await api.get(`/student-accounts/guardians/${id}`)).data,
  createGuardian: async (id, email) => (await api.post(`/student-accounts/guardians/${id}`, { email })).data,
  resendGuardian: async (id) => (await api.post(`/student-accounts/guardians/${id}/resend-activation`)).data,
  student: async (id) => (await api.get(`/student-accounts/students/${id}`)).data,
  createStudent: async (id, email = null) => (await api.post(`/student-accounts/students/${id}`, email ? { email } : {})).data,
  resendStudent: async (id) => (await api.post(`/student-accounts/students/${id}/resend-activation`)).data,
}
