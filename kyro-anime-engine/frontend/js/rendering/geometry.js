// frontend/js/rendering/geometry.js - small 2D helpers
export function distSeg(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy;
  let t = l2 ? ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2 : 0;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}

// Ramer-Douglas-Peucker (iterative). Keeps extra point fields (pressure).
export function rdp(pts, eps) {
  if (pts.length < 3) return pts.slice();
  const keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    let max = 0, idx = -1;
    for (let i = a + 1; i < b; i++) {
      const d = distSeg(pts[i], pts[a], pts[b]);
      if (d > max) { max = d; idx = i; }
    }
    if (idx > 0 && max > eps) { keep[idx] = 1; stack.push([a, idx], [idx, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}

export function strokeHit(points, x, y, r) {
  if (points.length === 1) return Math.hypot(points[0][0] - x, points[0][1] - y) <= r;
  const p = [x, y];
  for (let i = 1; i < points.length; i++) if (distSeg(p, points[i - 1], points[i]) <= r) return true;
  return false;
}

export function flattenPath(commands, curveSteps = 16) {
  const points = [];
  let current = null, start = null;
  for (const command of commands || []) {
    const [kind, ...coords] = command;
    if (kind === 'M') {
      current = [coords[0], coords[1]];
      start = current;
      points.push(current);
    } else if (kind === 'L') {
      current = [coords[0], coords[1]];
      points.push(current);
    } else if (kind === 'Q' && current) {
      const [cx, cy, x, y] = coords, origin = current;
      for (let step = 1; step <= curveSteps; step++) {
        const t = step / curveSteps, inverse = 1 - t;
        points.push([
          inverse * inverse * origin[0] + 2 * inverse * t * cx + t * t * x,
          inverse * inverse * origin[1] + 2 * inverse * t * cy + t * t * y,
        ]);
      }
      current = [x, y];
    } else if (kind === 'C' && current) {
      const [c1x, c1y, c2x, c2y, x, y] = coords, origin = current;
      for (let step = 1; step <= curveSteps; step++) {
        const t = step / curveSteps, inverse = 1 - t;
        points.push([
          inverse ** 3 * origin[0] + 3 * inverse ** 2 * t * c1x
            + 3 * inverse * t ** 2 * c2x + t ** 3 * x,
          inverse ** 3 * origin[1] + 3 * inverse ** 2 * t * c1y
            + 3 * inverse * t ** 2 * c2y + t ** 3 * y,
        ]);
      }
      current = [x, y];
    } else if (kind === 'Z' && current && start) {
      if (current[0] !== start[0] || current[1] !== start[1]) points.push(start);
      current = start;
    }
  }
  return points;
}

export function strokePathPoints(stroke) {
  return Array.isArray(stroke.points) ? stroke.points : flattenPath(stroke.commands);
}

// world -> layer-local, inverse of: translate(x,y) rotate scale translate(-anchor)
export function toLocal(t, x, y) {
  const th = (t.rotation || 0) * Math.PI / 180, c = Math.cos(th), s = Math.sin(th);
  const dx = x - (t.x || 0), dy = y - (t.y || 0);
  const rx = c * dx + s * dy, ry = -s * dx + c * dy;
  return [rx / ((t.scale_x ?? 1) || 1) + (t.anchor_x || 0), ry / ((t.scale_y ?? 1) || 1) + (t.anchor_y || 0)];
}

// layer-local -> world: translate(x,y) rotate scale translate(-anchor)
export function fromLocal(t, x, y) {
  const th = (t.rotation || 0) * Math.PI / 180, c = Math.cos(th), s = Math.sin(th);
  const sx = ((t.scale_x ?? 1)) * (x - (t.anchor_x || 0)), sy = ((t.scale_y ?? 1)) * (y - (t.anchor_y || 0));
  return [(t.x || 0) + c * sx - s * sy, (t.y || 0) + s * sx + c * sy];
}
