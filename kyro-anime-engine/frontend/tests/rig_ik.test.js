import test from 'node:test';
import assert from 'node:assert/strict';
import { applySavedIKConstraints, findIKTargetAtPoint, removeTwoBoneIK, solveTwoBoneIK, withTwoBoneIK } from '../js/animation/rig_ik.js';

test('two-bone IK solves a reachable target and reports the reachable endpoint', () => {
  const result = solveTwoBoneIK({ x: 0, y: 0 }, { x: 6, y: 8 }, 6, 6);
  assert.ok(Number.isFinite(result.shoulder));
  assert.ok(Number.isFinite(result.elbow));
  assert.ok(Math.abs(Math.hypot(result.reachableTarget.x, result.reachableTarget.y) - 10) < 1e-5);
  assert.ok(Math.abs(result.reach - 10) < 1e-5);
});

test('IK clamps unreachable targets to the chain reach', () => {
  const result = solveTwoBoneIK({ x: 2, y: 3 }, { x: 100, y: 3 }, 5, 4);
  assert.ok(result.reach < 9);
  assert.ok(Math.abs(result.reach - Math.hypot(result.reachableTarget.x - 2, result.reachableTarget.y - 3)) < 1e-5);
});

test('IK rejects invalid points and bone lengths', () => {
  assert.throws(() => solveTwoBoneIK({ x: 0, y: 0 }, { x: NaN, y: 2 }, 2, 3), /finite points/);
  assert.throws(() => solveTwoBoneIK({ x: 0, y: 0 }, { x: 2, y: 2 }, 0, 3), /positive bone lengths/);
});

test('IK constraint upsert preserves unrelated constraints and normalizes bend', () => {
  const original = [{ type: 'pin', bone_id: 'hand' }];
  const next = withTwoBoneIK(original, {
    id: 'left-arm-target', upperBoneId: 'upper_arm', lowerBoneId: 'forearm',
    targetX: 120, targetY: 80, bend: -4,
  });
  assert.equal(original.length, 1);
  assert.deepEqual(next[0], original[0]);
  assert.deepEqual(next[1], {
    type: 'ik_two_bone', id: 'left-arm-target', upper_bone_id: 'upper_arm',
    lower_bone_id: 'forearm', target: { x: 120, y: 80 }, bend: -1, enabled: true,
  });
  assert.equal(removeTwoBoneIK(next, 'left-arm-target').length, 1);
});

test('IK constraint validation rejects missing bones and invalid targets', () => {
  assert.throws(() => withTwoBoneIK([], {
    id: 'ik', upperBoneId: 'arm', lowerBoneId: 'arm', targetX: 1, targetY: 2,
  }), /two distinct bone IDs/);
  assert.throws(() => withTwoBoneIK([], {
    id: 'ik', upperBoneId: 'arm', lowerBoneId: 'elbow', targetX: Infinity, targetY: 2,
  }), /finite/);
});

test('saved IK target writes solved rotations into the procedural pose', () => {
  const rig = {
    bones: [
      { id: 'upper', pivot: { x: 0, y: 0 } },
      { id: 'lower', parent_id: 'upper', pivot: { x: 5, y: 0 } },
      { id: 'hand', parent_id: 'lower', name: 'hand', pivot: { x: 9, y: 0 } },
    ],
    constraints: [{
      type: 'ik_two_bone', id: 'arm-target', upper_bone_id: 'upper',
      lower_bone_id: 'lower', target: { x: 4, y: 5 }, bend: 1, enabled: true,
    }],
  };
  const pose = { bones: {} };
  assert.equal(applySavedIKConstraints(rig, pose), pose);
  assert.ok(Number.isFinite(pose.bones.upper));
  assert.ok(Number.isFinite(pose.bones.lower));
  assert.ok(Number.isFinite(pose.bones.hand));
});

test('saving the same bone pair replaces an imported IK target instead of duplicating it', () => {
  const imported = [{
    type: 'ik_two_bone', id: 'legacy-target', upper_bone_id: 'upper',
    lower_bone_id: 'lower', target: { x: 1, y: 2 }, bend: 1, enabled: true,
  }];
  const updated = withTwoBoneIK(imported, {
    id: 'ik_upper_lower', upperBoneId: 'upper', lowerBoneId: 'lower',
    targetX: 30, targetY: 40, bend: -1,
  });
  assert.equal(updated.filter(item => item.type === 'ik_two_bone').length, 1);
  assert.deepEqual(updated[0].target, { x: 30, y: 40 });
});

test('viewport hit-testing selects the nearest enabled IK target and respects radius', () => {
  const rig = { constraints: [
    { type: 'ik_two_bone', id: 'far', target: { x: 0, y: 0 } },
    { type: 'ik_two_bone', id: 'near', target: { x: 9, y: 0 } },
    { type: 'ik_two_bone', id: 'disabled', enabled: false, target: { x: 10, y: 0 } },
  ] };
  assert.equal(findIKTargetAtPoint(rig, { x: 10, y: 0 }, 4)?.id, 'near');
  assert.equal(findIKTargetAtPoint(rig, { x: 10, y: 0 }, 0.5), null);
  assert.equal(findIKTargetAtPoint(rig, { x: NaN, y: 0 }, 4), null);
});
