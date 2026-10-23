import test from 'node:test';
import assert from 'node:assert/strict';
import { snapPointToRigJoint } from '../js/animation/rig_snap.js';

test('snaps to the nearest bone endpoint within radius', () => {
  const bones = [{ id: 'upper', pivot: { x: 10, y: 20 }, rotation: 0, length: 40 }];
  assert.deepEqual(snapPointToRigJoint({ x: 48, y: 22 }, bones, 8), { x: 50, y: 20 });
});

test('snaps to a pivot when it is the nearest joint', () => {
  const bones = [{ id: 'root', pivot: { x: 10, y: 20 }, rotation: 90, length: 40 }];
  assert.deepEqual(snapPointToRigJoint({ x: 11, y: 22 }, bones, 5), { x: 10, y: 20 });
});

test('does not snap distant points or invalid inputs', () => {
  const bones = [{ id: 'root', pivot: { x: 10, y: 20 }, rotation: 0, length: 40 }];
  assert.equal(snapPointToRigJoint({ x: 500, y: 500 }, bones, 10), null);
  assert.equal(snapPointToRigJoint({ x: NaN, y: 0 }, bones, 10), null);
  assert.equal(snapPointToRigJoint({ x: 0, y: 0 }, bones, -1), null);
});
