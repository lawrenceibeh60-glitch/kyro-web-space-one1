import test from 'node:test';
import assert from 'node:assert/strict';

import { deformStrokeForRig } from '../js/animation/rig_deformer.js';

test('weighted vector points follow their bone transform', () => {
  const rig = { bones: [
    { id: 'arm', name: 'Arm', pivot: { x: 0, y: 0 }, rotation: 90 },
  ] };
  const stroke = {
    id: 'bendable', points: [[10, 0, 0.8], [0, 10, 0.4]],
    skin_weights: [
      [{ bone_id: 'arm', weight: 1 }],
      [{ bone_id: 'arm', weight: 1 }],
    ],
  };
  const result = deformStrokeForRig(stroke, rig, 0);
  assert.ok(Math.abs(result.points[0][0]) < 1e-8);
  assert.ok(Math.abs(result.points[0][1] - 10) < 1e-8);
  assert.equal(result.points[0][2], 0.8);
  assert.ok(Math.abs(result.points[1][0] + 10) < 1e-8);
  assert.ok(Math.abs(result.points[1][1]) < 1e-8);
  assert.equal(stroke.points[0][0], 10, 'deformation must not mutate source art');
});

test('partial skin weights blend the transformed point with the original point', () => {
  const rig = { bones: [
    { id: 'arm', name: 'Arm', pivot: { x: 0, y: 0 }, rotation: 90 },
  ] };
  const result = deformStrokeForRig({
    id: 'blend', points: [[10, 0]],
    skin_weights: [[{ bone_id: 'arm', weight: 0.5 }]],
  }, rig, 0);
  assert.ok(Math.abs(result.points[0][0] - 5) < 1e-8);
  assert.ok(Math.abs(result.points[0][1] - 5) < 1e-8);
});

test('weighted vector points inherit parent bone rotations', () => {
  const rig = { bones: [
    { id: 'torso', name: 'Torso', pivot: { x: 0, y: 0 }, rotation: 90 },
    { id: 'hand', name: 'Hand', parent_id: 'torso', pivot: { x: 10, y: 0 }, rotation: 0 },
  ] };
  const result = deformStrokeForRig({
    id: 'hand-art', points: [[10, 10]],
    skin_weights: [[{ bone_id: 'hand', weight: 1 }]],
  }, rig, 0);
  assert.ok(Math.abs(result.points[0][0] + 10) < 1e-8);
  assert.ok(Math.abs(result.points[0][1]) < 1e-8);
});
