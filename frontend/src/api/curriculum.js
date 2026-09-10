import { api } from './client'

const get = async (path) => (await api.get(path)).data
const send = async (method, path, payload) => (await api[method](path, payload)).data

export const curriculum = {
  platform: {
    list: () => get('/platform/curriculum/templates'),
    get: (id) => get(`/platform/curriculum/templates/${id}`),
    create: (payload) => send('post', '/platform/curriculum/templates', payload),
    update: (id, payload) => send('put', `/platform/curriculum/templates/${id}`, payload),
    clone: (id, payload = {}) => send('post', `/platform/curriculum/templates/${id}/clone`, payload),
    publish: (id) => send('post', `/platform/curriculum/templates/${id}/publish`),
    archive: (id) => send('post', `/platform/curriculum/templates/${id}/archive`),
  },
  school: {
    templates: () => get('/curriculum/templates'),
    configuration: () => get('/curriculum/configuration'),
    selectTemplate: (template_id, allow_local_customization = true) => send('post', '/curriculum/select-template', { template_id, allow_local_customization }),
  },
}
