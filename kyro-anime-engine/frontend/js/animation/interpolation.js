// frontend/js/animation/interpolation.js - easing + track evaluation.
// A keyframe's `ease` shapes the segment that STARTS at that key.
const EASE = {
  linear: t => t,
  hold: () => 0,
  ease_in: t => t * t,
  ease_out: t => 1 - (1 - t) * (1 - t),
  ease_in_out: t => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
};

function cubicBezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const X = u => ((ax * u + bx) * u + cx) * u, Y = u => ((ay * u + by) * u + cy) * u;
  const dX = u => (3 * ax * u + 2 * bx) * u + cx;
  return t => {
    if (t <= 0) return 0;
    if (t >= 1) return 1;
    let u = t;
    for (let i = 0; i < 8; i++) {
      const x = X(u) - t;
      if (Math.abs(x) < 1e-6) return Y(u);
      const d = dX(u);
      if (Math.abs(d) < 1e-6) break;
      u -= x / d;
    }
    let lo = 0, hi = 1; u = t;
    for (let i = 0; i < 30; i++) {
      const x = X(u);
      if (Math.abs(x - t) < 1e-6) break;
      if (x < t) lo = u; else hi = u;
      u = (lo + hi) / 2;
    }
    return Y(u);
  };
}

export function easeFn(ease) {
  if (ease && typeof ease === 'object' && Array.isArray(ease.bezier)) return cubicBezier(...ease.bezier);
  return EASE[ease] || EASE.linear;
}

export function evaluateTrack(track, frame) {
  const n = track.length;
  if (frame <= track[0].t) return track[0].v;
  if (frame >= track[n - 1].t) return track[n - 1].v;
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (track[m].t <= frame) lo = m; else hi = m; }
  const a = track[lo], b = track[hi];
  if (a.ease === 'hold') return a.v;
  return a.v + (b.v - a.v) * easeFn(a.ease)((frame - a.t) / (b.t - a.t));
}
