// Coalesce repeated invalidations into one frame draw. Injectable schedulers keep it testable.
export function createDrawQueue(draw, { request = callback => requestAnimationFrame(callback), cancel = id => cancelAnimationFrame(id) } = {}) {
  if (typeof draw !== 'function') throw new TypeError('draw must be a function');
  let scheduled = null, disposed = false, requested = 0, completed = 0;
  const flush = () => {
    scheduled = null;
    if (disposed) return;
    const target = requested;
    draw();
    completed = target;
  };
  return {
    request() { if (disposed) return; requested++; if (scheduled === null) scheduled = request(flush); },
    flush() { if (disposed) return; if (scheduled !== null) { cancel(scheduled); scheduled = null; } flush(); },
    cancel() { if (scheduled !== null) cancel(scheduled); scheduled = null; },
    dispose() { this.cancel(); disposed = true; },
    get pending() { return scheduled !== null; },
    get stats() { return { requested, completed, pending: scheduled !== null, disposed }; },
  };
}
