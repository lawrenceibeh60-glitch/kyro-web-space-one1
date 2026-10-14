// frontend/js/animation/pose_evaluator.js - layer transform / opacity at a frame (tracks override static values)
import { evaluateTrack } from './interpolation.js';

const DEFAULTS = { x: 0, y: 0, rotation: 0, rotation_y: 0, scale_x: 1, scale_y: 1, anchor_x: 0, anchor_y: 0 };
const ANIMATED = ['x', 'y', 'rotation', 'rotation_y', 'scale_x', 'scale_y'];

export function evaluateTransform(layer, frame) {
  const t = { ...DEFAULTS, ...(layer.transform || {}) };
  const tr = layer.tracks;
  if (tr) for (const ch of ANIMATED) if (tr[ch]?.length) t[ch] = evaluateTrack(tr[ch], frame);
  return t;
}

export function evaluateOpacity(layer, frame) {
  const tr = layer.tracks?.opacity;
  const v = tr?.length ? evaluateTrack(tr, frame) : (layer.opacity ?? 1);
  return Math.min(1, Math.max(0, v));
}
