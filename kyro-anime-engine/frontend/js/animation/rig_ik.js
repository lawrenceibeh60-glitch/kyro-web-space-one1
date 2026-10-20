// Deterministic two-bone IK helpers shared by the rig editor and animation runtime.
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export function solveTwoBoneIK(root, target, upperLength, lowerLength, bendDirection = 1) {
  if (![root?.x, root?.y, target?.x, target?.y, upperLength, lowerLength].every(Number.isFinite)
      || upperLength <= 0 || lowerLength <= 0) {
    throw new TypeError('IK requires finite points and positive bone lengths');
  }
  const dx = target.x - root.x;
  const dy = target.y - root.y;
  const distance = Math.hypot(dx, dy);
  const minReach = Math.abs(upperLength - lowerLength) + 1e-6;
  const maxReach = upperLength + lowerLength - 1e-6;
  const reach = clamp(distance || 1e-6, minReach, maxReach);
  const directionAngle = Math.atan2(dy, dx);
  const elbowCos = clamp(
    (upperLength ** 2 + lowerLength ** 2 - reach ** 2) / (2 * upperLength * lowerLength),
    -1, 1,
  );
  const shoulderCos = clamp(
    (upperLength ** 2 + reach ** 2 - lowerLength ** 2) / (2 * upperLength * reach),
    -1, 1,
  );
  const bend = bendDirection < 0 ? -1 : 1;
  const shoulder = directionAngle - bend * Math.acos(shoulderCos);
  const elbow = bend * (Math.PI - Math.acos(elbowCos));
  return {
    shoulder: shoulder * 180 / Math.PI,
    elbow: elbow * 180 / Math.PI,
    reach,
    reachableTarget: {
      x: root.x + Math.cos(directionAngle) * reach,
      y: root.y + Math.sin(directionAngle) * reach,
    },
  };
}

// Validate and immutably upsert a saved IK target constraint.
// bone IDs refer to the upper and lower bones; target coordinates are in project space.
export function withTwoBoneIK(constraints, {
  id, upperBoneId, lowerBoneId, targetX, targetY, bend = 1, enabled = true,
}) {
  if (typeof id !== 'string' || !id.trim()
      || typeof upperBoneId !== 'string' || !upperBoneId.trim()
      || typeof lowerBoneId !== 'string' || !lowerBoneId.trim()
      || upperBoneId === lowerBoneId) {
    throw new TypeError('IK requires an ID and two distinct bone IDs');
  }
  if (![targetX, targetY, bend].every(Number.isFinite) || bend === 0) {
    throw new TypeError('IK target and bend direction must be finite, and bend cannot be zero');
  }
  const remaining = (Array.isArray(constraints) ? constraints : [])
    .filter(item => !(item.type === 'ik_two_bone' && item.id === id));
  if (enabled) remaining.push({
    type: 'ik_two_bone', id, upper_bone_id: upperBoneId, lower_bone_id: lowerBoneId,
    target: { x: targetX, y: targetY }, bend: bend < 0 ? -1 : 1, enabled: true,
  });
  return remaining;
}

export function removeTwoBoneIK(constraints, id) {
  return (Array.isArray(constraints) ? constraints : [])
    .filter(item => !(item.type === 'ik_two_bone' && item.id === id));
}

export function applySavedIKConstraints(rig, pose) {
  if (!rig || !pose || !pose.bones) return pose;
  const bones = new Map((rig.bones || []).map(bone => [bone.id, bone]));
  for (const constraint of rig.constraints || []) {
    if (constraint.type !== 'ik_two_bone' || constraint.enabled === false) continue;
    const upper = bones.get(constraint.upper_bone_id);
    const lower = bones.get(constraint.lower_bone_id);
    const end = (rig.bones || []).find(bone => bone.parent_id === lower?.id && /hand|foot|ankle|wrist/i.test(bone.name || bone.id));
    const root = upper?.pivot;
    const joint = lower?.pivot;
    const endpoint = end?.pivot;
    const target = constraint.target;
    if (!root || !joint || !endpoint || !target
        || ![root.x, root.y, joint.x, joint.y, endpoint.x, endpoint.y, target.x, target.y].every(Number.isFinite)) continue;
    const upperLength = Math.hypot(joint.x - root.x, joint.y - root.y);
    const lowerLength = Math.hypot(endpoint.x - joint.x, endpoint.y - joint.y);
    if (upperLength < 1e-6 || lowerLength < 1e-6) continue;
    const solved = solveTwoBoneIK(root, target, upperLength, lowerLength, constraint.bend || 1);
    const restUpper = Math.atan2(joint.y - root.y, joint.x - root.x) * 180 / Math.PI;
    const restLower = Math.atan2(endpoint.y - joint.y, endpoint.x - joint.x) * 180 / Math.PI;
    const upperCorrection = solved.shoulder - restUpper;
    const lowerCorrection = solved.shoulder + solved.elbow - restLower - upperCorrection;
    pose.bones[upper.id] = upperCorrection;
    pose.bones[lower.id] = lowerCorrection;
    if (end) pose.bones[end.id] = -(upperCorrection + lowerCorrection);
  }
  return pose;
}
