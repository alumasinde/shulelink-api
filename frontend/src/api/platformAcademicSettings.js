import { api } from './client'

export async function listPlatformAcademicSettings() {
  const { data } = await api.get('/platform/academic-settings')
  return data
}

export async function updatePlatformAcademicSetting(id, payload) {
  const { data } = await api.patch(`/platform/academic-settings/${id}`, payload)
  return data
}
