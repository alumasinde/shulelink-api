import { api } from './client'

const blobGet = async (url) => (await api.get(url, { responseType: 'blob' })).data
const upload = async (url, file, mode) => {
  const form = new FormData(); form.append('file', file)
  return (await api.post(`${url}?mode=${encodeURIComponent(mode)}`, form, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}

export const dataTransfer = {
  template: async () => blobGet('/data-transfer/school-structure/template'),
  exportSchoolStructure: async () => blobGet('/data-transfer/school-structure/export'),
  importSchoolStructure: async (file, mode = 'create') => upload('/data-transfer/school-structure/import', file, mode),
  studentsTemplate: async () => blobGet('/data-transfer/students/template'),
  exportStudents: async () => blobGet('/data-transfer/students/export'),
  importStudents: async (file, mode = 'create') => upload('/data-transfer/students/import', file, mode),
  teachersTemplate: async () => blobGet('/data-transfer/academics/teachers/template'),
  exportTeachers: async () => blobGet('/data-transfer/academics/teachers/export'),
  importTeachers: async (file, mode = 'create') => upload('/data-transfer/academics/teachers/import', file, mode),
}
