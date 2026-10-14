// 2D linear-blend skinning for vector stroke points.
import { evaluateTrack } from './interpolation.js';

function rotationOf(bone, frame, pose) {
  const base = bone.tracks?.rotation?.length
    ? evaluateTrack(bone.tracks.rotation, frame)
    : (bone.rotation ?? 0);
  return base + (Number.isFinite(pose?.bones?.[bone.id]) ? pose.bones[bone.id] : 0);
}

function rotateAround(point, pivot, degrees) {
  const radians = degrees * Math.PI / 180;
  const cos = Math.cos(radians), sin = Math.sin(radians);
  const dx = point.x - pivot.x, dy = point.y - pivot.y;
  return {
    x: pivot.x + dx * cos - dy * sin,
    y: pivot.y + dx * sin + dy * cos,
  };
}

function boneChain(rig, boneId) {
  const byId = new Map((rig.bones || []).map(bone => [bone.id, bone]));
  const chain = [];
  const seen = new Set();
  let bone = byId.get(boneId);
  while (bone && !seen.has(bone.id)) {
    seen.add(bone.id);
    chain.unshift(bone);
    bone = bone.parent_id ? byId.get(bone.parent_id) : null;
  }
  return chain;
}

function transformPoint(point, chain, frame, pose) {
  let result = { x: point[0], y: point[1] };
  for (const bone of chain) {
    if (!bone.pivot || !Number.isFinite(bone.pivot.x) || !Number.isFinite(bone.pivot.y)) continue;
    result = rotateAround(result, bone.pivot, rotationOf(bone, frame, pose));
  }
  return result;
}

export function deformStrokeForRig(stroke, rig, frame, pose = null) {
  const weights = stroke?.skin_weights;
  const points = stroke?.points;
  if (!Array.isArray(weights) || !Array.isArray(points) || weights.length !== points.length) return stroke;
  const chains = new Map();
  const deformed = points.map((point, pointIndex) => {
    const influences = weights[pointIndex];
    if (!Array.isArray(influences) || !influences.length) return point.slice();
    let total = 0, x = 0, y = 0;
    for (const influence of influences) {
      const weight = Number(influence?.weight);
      const boneId = influence?.bone_id;
      if (!Number.isFinite(weight) || weight <= 0 || typeof boneId !== 'string') continue;
      if (!chains.has(boneId)) chains.set(boneId, boneChain(rig, boneId));
      const chain = chains.get(boneId);
      if (!chain.length) continue;
      const transformed = transformPoint(point, chain, frame, pose);
      x += transformed.x * weight;
      y += transformed.y * weight;
      total += weight;
    }
    if (total <= 0) return point.slice();
    const normalization = total > 1 ? 1 / total : 1;
    x *= normalization;
    y *= normalization;
    const remainder = Math.max(0, 1 - total);
    x += point[0] * remainder;
    y += point[1] * remainder;
    return [x, y, ...point.slice(2)];
  });
  return { ...stroke, points: deformed };
}
