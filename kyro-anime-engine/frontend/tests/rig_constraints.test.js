import test from 'node:test';
import assert from 'node:assert/strict';
import { clampBoneRotation, withRotationLimit } from '../js/animation/rig_constraints.js';

test('rotation limit clamps authored and animated local rotations', () => {
  const rig = { constraints: [{ type: 'rotation_limit', bone_id: 'elbow', min: -20, max: 45 }] };
  assert.equal(clampBoneRotation(rig, { id: 'elbow' }, 80), 45);
  assert.equal(clampBoneRotation(rig, { id: 'elbow' }, -80), -20);
  assert.equal(clampBoneRotation(rig, { id: 'elbow' }, 12), 12);
  assert.equal(clampBoneRotation(rig, { id: 'shoulder' }, 80), 80);
});

test('weighted rotation limits blend toward the legal angle', () => {
  const rig = { constraints: [{ type: 'rotation_limit', bone_id: 'knee', min: -30, max: 30, weight: 0.5 }] };
  assert.equal(clampBoneRotation(rig, { id: 'knee' }, 90), 60);
});

test('editing a rotation limit preserves unrelated constraints and is immutable', () => {
  const old = [{ type: 'pin', bone_id: 'hand' }, { type: 'rotation_limit', bone_id: 'knee', min: -10, max: 10 }];
  const next = withRotationLimit(old, 'knee', true, -25, 35, 0.8);
  assert.equal(old[1].min, -10);
  assert.deepEqual(next, [{ type: 'pin', bone_id: 'hand' }, { type: 'rotation_limit', bone_id: 'knee', min: -25, max: 35, weight: 0.8 }]);
  assert.deepEqual(withRotationLimit(next, 'knee', false), [{ type: 'pin', bone_id: 'hand' }]);
});

test('invalid rotation limits are rejected', () => {
  assert.throws(() => withRotationLimit([], 'knee', true, 40, -40), /minimum/);
  assert.throws(() => withRotationLimit([], 'knee', true, -30, 30, 2), /weight/);
});
