// KAE production animation clips: deterministic procedural motion, no demo-only runtime.
const TAU = Math.PI * 2;
const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
const smoothstep = (a, b, value) => {
  const t = clamp((value - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};

function normalizedName(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '_');
}

export function inferBoneRole(bone) {
  const name = normalizedName(`${bone?.name || ''}_${bone?.id || ''}`);
  const side = /(^|_)(left|l)(_|$)/.test(name) ? 'left'
    : /(^|_)(right|r)(_|$)/.test(name) ? 'right' : '';
  if (/pelvis|hips|hip_root|root/.test(name)) return 'pelvis';
  if (/torso|spine|chest|body/.test(name)) return 'torso';
  if (/head|neck/.test(name)) return 'head';
  if (/thigh|upper_leg|upleg|femur/.test(name)) return side ? `${side}_thigh` : 'thigh';
  if (/shin|lower_leg|calf|knee/.test(name)) return side ? `${side}_shin` : 'shin';
  if (/foot|ankle/.test(name)) return side ? `${side}_foot` : 'foot';
  if (/upper_arm|shoulder|bicep/.test(name)) return side ? `${side}_upper_arm` : 'upper_arm';
  if (/forearm|lower_arm|elbow/.test(name)) return side ? `${side}_forearm` : 'forearm';
  if (/hand|wrist/.test(name)) return side ? `${side}_hand` : 'hand';
  return 'generic';
}

export function solveTwoBoneIK(root, target, upperLength, lowerLength, bend = 1) {
  const dx = target.x - root.x;
  const dy = target.y - root.y;
  const distance = Math.hypot(dx, dy);
  if (![root.x, root.y, target.x, target.y, upperLength, lowerLength].every(Number.isFinite)
      || upperLength <= 0 || lowerLength <= 0) {
    throw new TypeError('IK requires finite points and positive bone lengths');
  }
  const minReach = Math.abs(upperLength - lowerLength) + 1e-6;
  const maxReach = upperLength + lowerLength - 1e-6;
  const reach = clamp(distance || 1e-6, minReach, maxReach);
  const base = Math.atan2(dy, dx);
  const elbowCos = clamp(
    (upperLength * upperLength + lowerLength * lowerLength - reach * reach)
      / (2 * upperLength * lowerLength), -1, 1,
  );
  const shoulderCos = clamp(
    (upperLength * upperLength + reach * reach - lowerLength * lowerLength)
      / (2 * upperLength * reach), -1, 1,
  );
  const direction = bend < 0 ? -1 : 1;
  return {
    shoulder: (base - direction * Math.acos(shoulderCos)) * 180 / Math.PI,
    elbow: direction * (Math.PI - Math.acos(elbowCos)) * 180 / Math.PI,
    reachableTarget: {
      x: root.x + Math.cos(base) * reach,
      y: root.y + Math.sin(base) * reach,
    },
    reach,
  };
}

export function evaluateWalkCycle(rig, frame, overrides = {}) {
  if (!Number.isFinite(frame)) throw new TypeError('frame must be finite');
  const config = { ...(rig?.animation || {}), ...overrides };
  const cycleFrames = clamp(Number(config.cycle_frames) || 24, 4, 240);
  const speed = clamp(Number(config.speed) || 1, 0.05, 8);
  const startFrame = Number.isFinite(config.start_frame) ? config.start_frame : 0;
  const elapsed = Math.max(0, frame - startFrame) * speed;
  const phaseFrame = config.loop === false ? Math.min(elapsed, cycleFrames) : elapsed % cycleFrames;
  const phase = phaseFrame / cycleFrames * TAU;
  const stride = clamp(Number(config.stride) || 24, 0, 100);
  const weight = clamp(Number(config.weight ?? 1), 0, 1);
  const left = Math.sin(phase);
  const right = Math.sin(phase + Math.PI);
  const stanceLeft = phase < Math.PI || phase >= TAU - 0.12;
  const stanceRight = !stanceLeft;
  const angles = {};
  const assign = (role, value) => { angles[role] = value * weight; };
  assign('pelvis', Math.sin(phase * 2) * 2.4);
  assign('torso', -Math.sin(phase * 2) * 1.8);
  assign('head', Math.sin(phase * 2) * 0.8);
  assign('left_thigh', left * stride * 0.72);
  assign('right_thigh', right * stride * 0.72);
  assign('left_shin', Math.max(0, -left) * stride * 0.8);
  assign('right_shin', Math.max(0, -right) * stride * 0.8);
  assign('left_foot', stanceLeft ? -left * stride * 0.12 : -stride * 0.18);
  assign('right_foot', stanceRight ? -right * stride * 0.12 : -stride * 0.18);
  assign('left_upper_arm', -left * stride * 0.42);
  assign('right_upper_arm', -right * stride * 0.42);
  assign('left_forearm', Math.max(0, left) * 7);
  assign('right_forearm', Math.max(0, right) * 7);

  const stanceBlend = Math.max(
    smoothstep(0.06, 0.24, Math.sin(phase) * 0.5 + 0.5),
    smoothstep(0.06, 0.24, Math.sin(phase + Math.PI) * 0.5 + 0.5),
  );
  return {
    clip: 'walk',
    frame,
    phase: phase / TAU,
    angles,
    rootOffset: {
      x: 0,
      y: -Math.abs(Math.sin(phase * 2)) * clamp(Number(config.bob) || 5, 0, 30) * weight,
    },
    footContact: { left: stanceLeft, right: stanceRight },
    contactWeight: clamp(stanceBlend, 0, 1),
  };
}

export function evaluateRigAnimation(rig, frame) {
  if (!rig?.animation || rig.animation.enabled === false) return null;
  if (rig.animation.type !== 'walk') return null;
  const pose = evaluateWalkCycle(rig, frame);
  const bones = {};
  for (const bone of rig.bones || []) {
    const role = inferBoneRole(bone);
    const clipAngle = pose.angles[role];
    if (Number.isFinite(clipAngle)) bones[bone.id] = clipAngle;
  }
  return { ...pose, bones };
}

export function blendRigRotation(baseRotation, clipRotation, weight = 1) {
  const base = Number.isFinite(baseRotation) ? baseRotation : 0;
  if (!Number.isFinite(clipRotation)) return base;
  return base + (clipRotation - base) * clamp(weight, 0, 1);
}
