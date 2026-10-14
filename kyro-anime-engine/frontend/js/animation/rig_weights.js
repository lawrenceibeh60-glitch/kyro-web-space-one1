// Shared bone-weight operations used by the rig authoring UI.
export function paintBoneInfluence(existing, boneId, targetWeight) {
  const target = Math.max(0.01, Math.min(1, Number(targetWeight) || 0.01));
  const source = Array.isArray(existing) ? existing : [];
  const others = source.filter(item => item?.bone_id !== boneId && Number(item?.weight) > 0);
  const otherTotal = others.reduce((sum, item) => sum + Number(item.weight), 0);
  const remainder = Math.max(0, 1 - target);
  const normalizedOthers = otherTotal > 0
    ? others.map(item => ({ bone_id: item.bone_id, weight: Number(item.weight) * remainder / otherTotal }))
    : [];
  return [...normalizedOthers, { bone_id: boneId, weight: target }];
}

export function nearestBoneInfluence(point, bones) {
  let nearest = null, best = Infinity;
  for (const bone of bones || []) {
    if (!Number.isFinite(bone.pivot?.x) || !Number.isFinite(bone.pivot?.y)) continue;
    const distance = (point[0] - bone.pivot.x) ** 2 + (point[1] - bone.pivot.y) ** 2;
    if (distance < best) { best = distance; nearest = bone; }
  }
  return nearest ? [{ bone_id: nearest.id, weight: 1 }] : [];
}
