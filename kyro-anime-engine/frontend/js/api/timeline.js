import { request } from './client.js';

export const Timeline = {
  summary: projectId => request('GET', `/api/projects/${encodeURIComponent(projectId)}/timeline`),
  setKeyframe: (projectId, payload) => request('POST', `/api/projects/${encodeURIComponent(projectId)}/timeline/keyframe`, payload),
  deleteKeyframe: (projectId, payload) => request('DELETE', `/api/projects/${encodeURIComponent(projectId)}/timeline/keyframe`, payload),
  applyScript: (projectId, script) => request('POST', `/api/projects/${encodeURIComponent(projectId)}/timeline/script`, script),
};
