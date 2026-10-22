import { evaluateTrack } from './interpolation.js';

const finite = (value, fallback = 0) => Number.isFinite(value) ? value : fallback;

function rotatePoint(point, origin, degrees) {
  const radians = degrees * Math.PI / 180;
  const cos = Math.cos(radians);
  const sin = Math.sin(radians);
  const x = point.x - origin.x;
  const y = point.y - origin.y;
  return {
    x: origin.x + x * cos - y * sin,
    y: origin.y + x * sin + y * cos,
  };
}

function validateRig(rig) {
  if (!rig || !Array.isArray(rig.bones)) throw new TypeError('Rig must contain a bones array.');
  const ids = new Set();
  for (const bone of rig.bones) {
    if (!bone || typeof bone.id !== 'string' || !bone.id) throw new TypeError('Every bone needs a non-empty id.');
    if (ids.has(bone.id)) throw new TypeError(`Duplicate bone id: ${bone.id}`);
    ids.add(bone.id);
    if (!bone.pivot || !Number.isFinite(bone.pivot.x) || !Number.isFinite(bone.pivot.y)) {
      throw new TypeError(`Bone ${bone.id} needs a finite pivot.`);
    }
    for (const key of bone.tracks?.rotation || []) {
      if (!Number.isInteger(key.t) || key.t < 0 || !Number.isFinite(key.v)) {
        throw new TypeError(`Bone ${bone.id} has an invalid rotation keyframe.`);
      }
    }
  }
  for (const bone of rig.bones) {
    if (bone.parent_id != null && !ids.has(bone.parent_id)) {
      throw new TypeError(`Bone ${bone.id} references missing parent ${bone.parent_id}.`);
    }
  }
}

export function resolveRigFrame(rig, frame, { loop = true } = {}) {
  const start = Math.max(0, Math.floor(finite(rig?.animation?.start_frame, 0)));
  const cycle = Math.floor(finite(rig?.animation?.cycle_frames, 0));
  const local = Math.max(0, finite(frame, 0) - start);
  if (loop && rig?.animation?.loop !== false && cycle >= 1) return local % cycle;
  return local;
}

/**
 * Evaluate a KAE rig at a zero-based frame.
 * Bone pivots are authored in project-space rest coordinates; child pivots follow
 * their parent's evaluated rotation. Rotation tracks use the native animation
 * schema's keyframe format: [{t, v, ease?}].
 */
export function evaluateRig(rig, frame, options = {}) {
  validateRig(rig);
  const evaluatedFrame = resolveRigFrame(rig, frame, options);
  const byId = new Map(rig.bones.map(bone => [bone.id, bone]));
  const result = new Map();
  const visiting = new Set();

  function visit(bone) {
    if (result.has(bone.id)) return result.get(bone.id);
    if (visiting.has(bone.id)) throw new TypeError(`Rig contains a parent cycle at bone ${bone.id}.`);
    visiting.add(bone.id);

    const parent = bone.parent_id ? visit(byId.get(bone.parent_id)) : null;
    const track = bone.tracks?.rotation;
    const rotation = track?.length ? evaluateTrack(track, evaluatedFrame) : finite(bone.rotation, 0);
    const worldPivot = parent
      ? rotatePoint(bone.pivot, byId.get(bone.parent_id).pivot, parent.worldRotation)
      : { x: bone.pivot.x, y: bone.pivot.y };
    const evaluated = {
      id: bone.id,
      parent_id: bone.parent_id ?? null,
      pivot: { x: bone.pivot.x, y: bone.pivot.y },
      worldPivot,
      localRotation: rotation,
      worldRotation: (parent?.worldRotation || 0) + rotation,
      length: Math.max(0, finite(bone.length, 0)),
    };
    visiting.delete(bone.id);
    result.set(bone.id, evaluated);
    return evaluated;
  }

  for (const bone of rig.bones) visit(bone);
  return { frame: evaluatedFrame, bones: rig.bones.map(bone => result.get(bone.id)) };
}
