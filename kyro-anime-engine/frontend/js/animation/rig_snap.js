// Project-space snapping helpers for Character Line Tracement and rig editing.
export function snapPointToRigJoint(point, bones, radius = 24) {
  if (!Number.isFinite(point?.x) || !Number.isFinite(point?.y)
      || !Number.isFinite(radius) || radius < 0) return null;
  let best = null;
  let bestDistance = radius;
  for (const bone of Array.isArray(bones) ? bones : []) {
    if (!Number.isFinite(bone?.pivot?.x) || !Number.isFinite(bone?.pivot?.y)) continue;
    const angle = (Number(bone.rotation) || 0) * Math.PI / 180;
    const length = Math.max(0, Number(bone.length) || 0);
    const candidates = [
      { x: bone.pivot.x, y: bone.pivot.y },
      { x: bone.pivot.x + Math.cos(angle) * length, y: bone.pivot.y + Math.sin(angle) * length },
    ];
    for (const candidate of candidates) {
      const distance = Math.hypot(candidate.x - point.x, candidate.y - point.y);
      if (distance <= bestDistance) {
        bestDistance = distance;
        best = candidate;
      }
    }
  }
  return best ? { x: best.x, y: best.y } : null;
}
