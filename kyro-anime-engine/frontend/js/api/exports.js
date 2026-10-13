// frontend/js/api/exports.js
import { request } from './client.js';

export const Exports = {
  capabilities: () => request('GET', '/api/exports/capabilities'),
  create: opts => request('POST', '/api/exports', opts),
  finish: job => request('POST', `/api/exports/${job}/finish`),
  async putFrame(job, index, blob) {
    const res = await fetch(`/api/exports/${job}/frames/${index}`, { method: 'PUT', headers: { 'Content-Type': 'image/png' }, body: blob });
    if (!res.ok) {
      let msg = res.statusText;
      try { msg = (await res.json()).error || msg; } catch (_) { /* no body */ }
      throw new Error(msg);
    }
  },
};
