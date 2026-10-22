import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { evaluateRig, resolveRigFrame } from '../js/animation/bone_evaluator.js';

const rig = JSON.parse(await readFile(new URL('./fixtures/rigged_arm_idle.json', import.meta.url), 'utf8'));

test('rigged idle fixture has a stable hierarchy and interpolates keyed arm rotations', () => {
  const start = evaluateRig(rig, 0);
  const middle = evaluateRig(rig, 6);
  const end = evaluateRig(rig, 12);
  assert.equal(start.bones.length, 3);
  assert.equal(start.bones[1].id, 'upper_arm');
  assert.equal(start.bones[1].localRotation, -25);
  assert.ok(middle.bones[1].localRotation > -25 && middle.bones[1].localRotation < 35);
  assert.equal(end.bones[1].localRotation, 35);
  assert.notDeepEqual(start.bones[2].worldPivot, middle.bones[2].worldPivot);
});

test('looping wraps to the start pose and respects the configured start frame', () => {
  assert.equal(resolveRigFrame(rig, 24), 0);
  assert.equal(resolveRigFrame({ ...rig, animation: { ...rig.animation, start_frame: 10 } }, 10), 0);
  assert.equal(resolveRigFrame({ ...rig, animation: { ...rig.animation, loop: false } }, 30), 30);
  assert.equal(evaluateRig(rig, 24).bones[1].localRotation, -25);
});

test('invalid parents and cyclic rigs are rejected instead of hanging playback', () => {
  assert.throws(() => evaluateRig({ ...rig, bones: [{ ...rig.bones[0], parent_id: 'missing' }] }, 0), /missing parent/);
  const cyclic = { ...rig, bones: rig.bones.map(b => ({ ...b })) };
  cyclic.bones[0].parent_id = 'forearm';
  assert.throws(() => evaluateRig(cyclic, 0), /parent cycle/);
});

test('invalid rotation keyframes are rejected', () => {
  const invalid = { ...rig, bones: rig.bones.map(b => ({ ...b, tracks: b.tracks ? { ...b.tracks, rotation: [...b.tracks.rotation] } : undefined })) };
  invalid.bones[1].tracks.rotation[1] = { t: -1, v: NaN };
  assert.throws(() => evaluateRig(invalid, 0), /invalid rotation keyframe/);
});
