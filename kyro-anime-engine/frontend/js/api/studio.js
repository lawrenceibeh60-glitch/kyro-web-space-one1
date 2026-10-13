import { request } from './client.js';

export const Effects = {
  list: projectId => request('GET', `/api/projects/${encodeURIComponent(projectId)}/effects`),
  create: (projectId, effect) => request('POST', `/api/projects/${encodeURIComponent(projectId)}/effects`, effect),
  update: (projectId, id, effect) => request('PUT', `/api/projects/${encodeURIComponent(projectId)}/effects/${encodeURIComponent(id)}`, effect),
  remove: (projectId, id) => request('DELETE', `/api/projects/${encodeURIComponent(projectId)}/effects/${encodeURIComponent(id)}`),
};

export const Rigs = {
  list: projectId => request('GET', `/api/projects/${encodeURIComponent(projectId)}/rigs`),
  create: (projectId, rig) => request('POST', `/api/projects/${encodeURIComponent(projectId)}/rigs`, rig),
  update: (projectId, id, rig) => request('PUT', `/api/projects/${encodeURIComponent(projectId)}/rigs/${encodeURIComponent(id)}`, rig),
  remove: (projectId, id) => request('DELETE', `/api/projects/${encodeURIComponent(projectId)}/rigs/${encodeURIComponent(id)}`),
};

export const StudioCharacters = {
  generate: (projectId, options) => request(
    'POST',
    `/api/projects/${encodeURIComponent(projectId)}/characters/generate`,
    options,
  ),
};

export const Audio = {
  upload: async (projectId, file, metadata) => {
    const body = new FormData();
    body.set('file', file);
    for (const [key, value] of Object.entries(metadata)) body.set(key, String(value));
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/audio`, {
      method: 'POST',
      body,
    });
    let result = null;
    try { result = await response.json(); } catch (_) { /* empty response */ }
    if (!response.ok) {
      const error = new Error(result?.error || response.statusText);
      error.status = response.status;
      error.details = result?.details || [];
      throw error;
    }
    return result;
  },
  remove: (projectId, id) => request(
    'DELETE',
    `/api/projects/${encodeURIComponent(projectId)}/audio/${encodeURIComponent(id)}`,
  ),
};
