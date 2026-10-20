// Native timeline math shared by the dope sheet and playback controls.
// Frames and exposure starts are zero-based internally; the UI displays one-based frames.
export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
export function frameFromTimelineX(x, padding, pixelsPerFrame, totalFrames) {
  if (!Number.isFinite(x) || !Number.isFinite(padding) || !Number.isFinite(pixelsPerFrame) || pixelsPerFrame <= 0) return 0;
  return clamp(Math.floor((x - padding) / pixelsPerFrame), 0, Math.max(0, Math.floor(Number(totalFrames) || 1) - 1));
}
export function exposureBounds(exposures, index, totalFrames) {
  const total = Math.max(1, Math.floor(Number(totalFrames) || 1));
  const ordered = [...(Array.isArray(exposures) ? exposures : [])].sort((a, b) => a.start - b.start);
  const current = ordered[index];
  if (!current) return null;
  const previousEnd = index > 0 ? ordered[index - 1].start + ordered[index - 1].length : 0;
  const nextStart = index + 1 < ordered.length ? ordered[index + 1].start : total;
  return { previousEnd: clamp(previousEnd, 0, total), nextStart: clamp(nextStart, 0, total), total };
}
export function previewExposureEdit(original, edge, delta, bounds) {
  if (!original || !bounds || !Number.isFinite(delta)) return original ? { ...original } : null;
  const item = { ...original };
  const start = Math.max(0, Math.floor(Number(item.start) || 0));
  const length = Math.max(1, Math.floor(Number(item.length) || 1));
  const end = start + length;
  if (edge === 'move') item.start = clamp(start + Math.round(delta), bounds.previousEnd, Math.max(bounds.previousEnd, bounds.nextStart - length));
  else if (edge === 'left') { item.start = clamp(start + Math.round(delta), bounds.previousEnd, end - 1); item.length = end - item.start; }
  else if (edge === 'right') item.length = clamp(end + Math.round(delta), start + 1, bounds.nextStart) - start;
  return item;
}
export function validateExposureTrack(exposures, totalFrames) {
  const total = Math.max(1, Math.floor(Number(totalFrames) || 1));
  if (!Array.isArray(exposures)) return { valid: false, reason: 'Exposures must be an array.' };
  let previousEnd = 0;
  for (const exposure of [...exposures].sort((a, b) => a.start - b.start)) {
    if (!Number.isInteger(exposure?.start) || !Number.isInteger(exposure?.length) || exposure.start < 0 || exposure.length < 1) return { valid: false, reason: 'Exposure start must be a non-negative integer and length must be a positive integer.' };
    if (exposure.start < previousEnd) return { valid: false, reason: 'Drawing exposures cannot overlap.' };
    if (exposure.start + exposure.length > total) return { valid: false, reason: 'Drawing exposure extends beyond the scene duration.' };
    if (typeof exposure.drawing !== 'string' || !exposure.drawing) return { valid: false, reason: 'Every exposure must reference a drawing.' };
    previousEnd = exposure.start + exposure.length;
  }
  return { valid: true, reason: null };
}
