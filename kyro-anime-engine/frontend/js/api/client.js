// frontend/js/api/client.js
export async function request(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
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
