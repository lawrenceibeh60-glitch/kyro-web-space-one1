// frontend/js/api/client.js
export async function request(method, url, body) {
  let payload = body;
  if (payload && typeof payload === 'object' && ['/api/ai/chat', '/api/ai/video/analyze', '/api/ai/video/reconstruction/plan', '/api/ai/animation/plan'].includes(url)) {
    try {
      const saved = sessionStorage.getItem('kae-ai-provider-config');
      if (saved && !payload.provider_config) payload = { ...payload, provider_config: JSON.parse(saved) };
    } catch (_) { /* ignore unavailable session storage */ }
  }
  const res = await fetch(url, {
    method,
    headers: payload ? { 'Content-Type': 'application/json' } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const err = new Error(data?.error || res.statusText);
    err.status = res.status; err.details = data?.details || [];
    throw err;
  }
  return data;
}
