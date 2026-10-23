// Bounded LRU cache for expensive rendered frame/asset results.
// Values with dimensions are budgeted by their RGBA footprint; other values use a conservative estimate.
export function createRenderCache({ maxEntries = 120, maxBytes = 32 * 1024 * 1024 } = {}) {
  const entries = new Map();
  let bytes = 0, hits = 0, misses = 0;
  const estimate = value => {
    if (value && Number.isFinite(value.width) && Number.isFinite(value.height)) return Math.max(1, value.width * value.height * 4);
    if (typeof value === 'string') return Math.max(1, value.length * 2);
    if (value instanceof ArrayBuffer) return Math.max(1, value.byteLength);
    if (ArrayBuffer.isView(value)) return Math.max(1, value.byteLength);
    try { return Math.max(64, JSON.stringify(value).length * 2); } catch { return 256; }
  };
  const remove = key => { const item = entries.get(key); if (!item) return false; bytes -= item.bytes; entries.delete(key); return true; };
  return {
    get size() { return entries.size; },
    get bytes() { return bytes; },
    get stats() { return { size: entries.size, bytes, hits, misses, maxEntries, maxBytes }; },
    get(key) {
      if (!entries.has(key)) { misses++; return undefined; }
      const item = entries.get(key); entries.delete(key); entries.set(key, item); hits++; return item.value;
    },
    set(key, value, cost) {
      if (key == null) throw new TypeError('Render cache keys must not be null');
      remove(key);
      const weight = Math.max(1, Number.isFinite(cost) ? cost : estimate(value));
      if (weight > maxBytes || maxEntries < 1) return value;
      entries.set(key, { value, bytes: weight }); bytes += weight;
      while (entries.size > maxEntries || bytes > maxBytes) remove(entries.keys().next().value);
      return value;
    },
    delete: remove,
    clear() { entries.clear(); bytes = 0; hits = 0; misses = 0; },
    has(key) { return entries.has(key); },
  };
}
export const renderCache = createRenderCache();
