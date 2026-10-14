// 2D linear-blend skinning for point strokes and vector path control points.
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
  return { x: pivot.x + dx * cos - dy * sin, y: pivot.y + dx * sin + dy * cos };
}

function boneChain(rig, boneId) {
  const byId = new Map((rig.bones || []).map(bone => [bone.id, bone]));
  const chain = [], seen = new Set();
  let bone = byId.get(boneId);
  while (bone && !seen.has(bone.id)) {
    seen.add(bone.id); chain.unshift(bone);
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

function deformCoordinate(pair, influences, rig, frame, pose, chains) {
  if (!Array.isArray(pair) || pair.length < 2 || !Array.isArray(influences) || !influences.length) {
    return Array.isArray(pair) ? [...pair] : pair;
  }
  let total = 0, x = 0, y = 0;
  for (const influence of influences) {
    const weight = Number(influence?.weight), boneId = influence?.bone_id;
    if (!Number.isFinite(weight) || weight <= 0 || typeof boneId !== 'string') continue;
    if (!chains.has(boneId)) chains.set(boneId, boneChain(rig, boneId));
    const chain = chains.get(boneId);
    if (!chain.length) continue;
    const transformed = transformPoint(pair, chain, frame, pose);
    x += transformed.x * weight; y += transformed.y * weight; total += weight;
  }
  if (total <= 0) return [...pair];
  const normalization = total > 1 ? 1 / total : 1;
  x *= normalization; y *= normalization;
  const remainder = Math.max(0, 1 - total);
  x += pair[0] * remainder; y += pair[1] * remainder;
  return [x, y, ...pair.slice(2)];
}

export function pathCoordinateCount(commands) {
  if (!Array.isArray(commands)) return 0;
  return commands.reduce((total, command) => {
    if (!Array.isArray(command)) return total;
    if (command[0] === 'M' || command[0] === 'L') return total + 1;
    if (command[0] === 'Q') return total + 2;
    if (command[0] === 'C') return total + 3;
    return total;
  }, 0);
}

export function deformStrokeForRig(stroke, rig, frame, pose = null) {
  const chains = new Map();
  let result = stroke;
  if (Array.isArray(stroke?.points) && Array.isArray(stroke?.skin_weights)
      && stroke.skin_weights.length === stroke.points.length) {
    result = {
      ...result,
      points: stroke.points.map((point, index) =>
        deformCoordinate(point, stroke.skin_weights[index], rig, frame, pose, chains)),
    };
  }
  if (Array.isArray(stroke?.commands) && Array.isArray(stroke?.command_skin_weights)
      && stroke.command_skin_weights.length === pathCoordinateCount(stroke.commands)) {
    let coordinateIndex = 0;
    result = {
      ...result,
      commands: stroke.commands.map(command => {
        if (!Array.isArray(command) || command[0] === 'Z') return [...command];
        const next = [...command];
        for (let index = 1; index + 1 < command.length; index += 2) {
          const pair = [command[index], command[index + 1]];
          const deformed = deformCoordinate(pair, stroke.command_skin_weights[coordinateIndex++], rig, frame, pose, chains);
          next[index] = deformed[0]; next[index + 1] = deformed[1];
        }
        return next;
      }),
    };
  }
  return result;
}
