// frontend/js/api/projects.js
import { request } from './client.js';

export const Projects = {
  list: () => request('GET', '/api/projects').then(r => r.projects),
  create: (name, settings) => request('POST', '/api/projects', { name, settings }),
  template: async template => request('POST', `/api/projects/templates/${encodeURIComponent(template)}`),
  // Backwards-compatible names for older integrations.
  demo: async () => request('POST', '/api/projects/templates/bounce'),
  demoTemplate: async template => request('POST', `/api/projects/templates/${encodeURIComponent(template)}`),
  import: payload => request('POST', '/api/projects/import', payload),
  get: id => request('GET', `/api/projects/${encodeURIComponent(id)}`),
  save: (id, doc, expectedModified) => request('PUT', `/api/projects/${encodeURIComponent(id)}`, expectedModified ? { ...doc, _expected_modified: expectedModified } : doc),
  remove: id => request('DELETE', `/api/projects/${encodeURIComponent(id)}`),
};
