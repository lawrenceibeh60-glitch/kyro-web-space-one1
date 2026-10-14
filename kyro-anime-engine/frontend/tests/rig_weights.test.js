import test from 'node:test';
import assert from 'node:assert/strict';

import { paintBoneInfluence, nearestBoneInfluence } from '../js/animation/rig_weights.js';

test('painting adds a selected influence while preserving other bones and a valid total', () => {
  const next = paintBoneInfluence([
    { bone_id: 'upper', weight: 0.7 },
    { bone_id: 'lower', weight: 0.3 },
  ], 'upper', 0.6);
  assert.deepEqual(next, [
    { bone_id: 'lower', weight: 0.4 },
    { bone_id: 'upper', weight: 0.6 },
  ]);
  assert.ok(Math.abs(next.reduce((sum, item) => sum + item.weight, 0) - 1) < 1e-9);
});

test('painting an unweighted point supports partial influence without mutating source', () => {
  const original = [];
  const next = paintBoneInfluence(original, 'arm', 0.35);
  assert.deepEqual(next, [{ bone_id: 'arm', weight: 0.35 }]);
  assert.deepEqual(original, []);
});

test('auto-weight chooses the nearest valid bone pivot and skips invalid pivots', () => {
  const bones = [
    { id: 'invalid', pivot: { x: NaN, y: 0 } },
    { id: 'near', pivot: { x: 11, y: 12 } },
    { id: 'far', pivot: { x: 100, y: 100 } },
  ];
  assert.deepEqual(nearestBoneInfluence([10, 10], bones), [{ bone_id: 'near', weight: 1 }]);
  assert.deepEqual(nearestBoneInfluence([0, 0], []), []);
});
