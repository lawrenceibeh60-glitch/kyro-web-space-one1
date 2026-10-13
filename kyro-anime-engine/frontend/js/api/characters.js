import { request } from './client.js';

export const Characters = {
  import: (projectId, character) => request(
    'POST',
    `/api/projects/${encodeURIComponent(projectId)}/characters/import`,
    character,
  ),
};
