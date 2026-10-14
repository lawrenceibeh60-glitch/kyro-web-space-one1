import test from 'node:test';
import assert from 'node:assert/strict';

import { buildAutoRig } from '../js/animation/auto_rig.js';

const part = (id, name, points) => ({ id, name, strokes: [{ id: `stroke_${id}`, points }] });

test('auto-rig creates one bone per part with geometry-derived pivots and useful parent chains', () => {
  const character = {
    id: 'hero', name: 'Hero',
    parts: [
      part('torso', 'Torso', [[40, 20], [60, 100]]),
      part('head', 'Head', [[42, 0], [58, 20]]),
      part('left_upper_arm', 'Left upper arm', [[20, 30], [40, 60]]),
      part('left_forearm', 'Left forearm', [[5, 60], [20, 90]]),
      part('left_hand', 'Left hand', [[0, 90], [5, 100]]),
      part('left_thigh', 'Left thigh', [[42, 100], [48, 140]]),
      part('left_shin', 'Left shin', [[40, 140], [45, 180]]),
      part('left_foot', 'Left foot', [[20, 180], [45, 190]]),
      { id: 'accessory', name: 'Accessory', strokes: [] },
    ],
  };
  const { rig, addedCount, totalCount } = buildAutoRig(character, null, { width: 1280, height: 720 });
  assert.equal(addedCount, character.parts.length);
  assert.equal(totalCount, character.parts.length);
  const bones = new Map(rig.bones.map(bone => [bone.character_part_id, bone]));
  assert.equal(bones.get('head').pivot.y, 20);
  assert.equal(bones.get('torso').pivot.y, 37.6);
  assert.equal(bones.get('accessory').pivot.x, 640);
  assert.equal(bones.get('accessory').pivot.y, 360);
  assert.equal(bones.get('head').parent_id, bones.get('torso').id);
  assert.equal(bones.get('left_forearm').parent_id, bones.get('left_upper_arm').id);
  assert.equal(bones.get('left_hand').parent_id, bones.get('left_forearm').id);
  assert.equal(bones.get('left_shin').parent_id, bones.get('left_thigh').id);
  assert.equal(bones.get('left_foot').parent_id, bones.get('left_shin').id);
});

test('auto-rig preserves existing bones and only adds missing parts', () => {
  const character = {
    id: 'hero', name: 'Hero',
    parts: [part('torso', 'Torso', [[10, 10], [30, 60]]), part('head', 'Head', [[12, 0], [28, 10]])],
  };
  const existing = {
    id: 'manual_rig', name: 'Manual Rig', character_id: 'hero',
    bones: [{ id: 'root_custom', name: 'Custom Root', character_part_id: 'torso',
      pivot: { x: 21, y: 41 }, rotation: 12 }],
  };
  const { rig, addedCount } = buildAutoRig(character, existing, { width: 1280, height: 720 });
  assert.equal(addedCount, 1);
  assert.equal(rig.id, 'manual_rig');
  assert.equal(rig.bones[0].id, 'root_custom');
  assert.deepEqual(rig.bones[0].pivot, { x: 21, y: 41 });
  assert.equal(rig.bones[1].parent_id, 'root_custom');
});

test('auto-rig rejects an empty character', () => {
  assert.throws(() => buildAutoRig({ id: 'empty', parts: [] }), /no parts to rig/i);
});
