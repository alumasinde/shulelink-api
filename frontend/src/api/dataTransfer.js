import { api } from './client'

export const dataTransfer = {
  template: async () => {
    const response = await api.get('/data-transfer/school-structure/template', { responseType: 'blob' })
    return response.data
  },
  exportSchoolStructure: async () => {
    const response = await api.get('/data-transfer/school-structure/export', { responseType: 'blob' })
    return response.data
  },
  importSchoolStructure: async (file, mode = 'create') => {
    const form = new FormData()
    form.append('file', file)
    const response = await api.post(`/data-transfer/school-structure/import?mode=${encodeURIComponent(mode)}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },
}
