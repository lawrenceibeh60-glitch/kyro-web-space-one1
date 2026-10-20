// Constraint evaluation for native character rigs. Angles are stored in degrees.
const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

export function clampBoneRotation(rig, bone, rotation) {
  if (!Number.isFinite(rotation) || !bone?.id) return rotation;
  let result = rotation;
  for (const constraint of Array.isArray(rig?.constraints) ? rig.constraints : []) {
    if (constraint?.type !== 'rotation_limit' || constraint.bone_id !== bone.id) continue;
    const min = Number.isFinite(constraint.min) ? constraint.min : -Infinity;
    const max = Number.isFinite(constraint.max) ? constraint.max : Infinity;
    if (min > max) continue;
    const limited = clamp(result, min, max);
    const weight = Number.isFinite(constraint.weight) ? clamp(constraint.weight, 0, 1) : 1;
    result += (limited - result) * weight;
  }
  return result;
}

export function withRotationLimit(constraints, boneId, enabled, min, max, weight = 1) {
  if (typeof boneId !== 'string' || !boneId) throw new TypeError('A bone ID is required.');
  const existing = (Array.isArray(constraints) ? constraints : [])
    .filter(item => !(item?.type === 'rotation_limit' && item.bone_id === boneId));
  if (!enabled) return existing;
  if (!Number.isFinite(min) || !Number.isFinite(max) || min > max) {
    throw new RangeError('Rotation limit minimum must be finite and no greater than its maximum.');
  }
  if (!Number.isFinite(weight) || weight < 0 || weight > 1) {
    throw new RangeError('Constraint weight must be between 0 and 1.');
  }
  return [...existing, { type: 'rotation_limit', bone_id: boneId, min, max, weight }];
}
