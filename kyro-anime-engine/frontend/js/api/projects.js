// frontend/js/api/projects.js
import { request } from './client.js';

export const Projects = {
  list: () => request('GET', '/api/projects').then(r => r.projects),
  create: (name, settings) => request('POST', '/api/projects', { name, settings }),
  demo: async () => {
    try { return await request('POST', '/api/projects/demo'); }
    catch (error) {
      if (error.status !== 405) throw error;
      return request('GET', '/api/projects/demo');
    }
  },
  demoTemplate: async template => {
    const path = `/api/projects/demo/${encodeURIComponent(template)}`;
    try { return await request('POST', path); }
    catch (error) {
      if (error.status !== 405) throw error;
      return request('GET', path);
    }
  },
  import: payload => request('POST', '/api/projects/import', payload),
  get: id => request('GET', `/api/projects/${encodeURIComponent(id)}`),
  save: (id, doc) => request('PUT', `/api/projects/${encodeURIComponent(id)}`, doc),
  remove: id => request('DELETE', `/api/projects/${encodeURIComponent(id)}`),
};
