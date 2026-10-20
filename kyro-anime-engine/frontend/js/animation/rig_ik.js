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
