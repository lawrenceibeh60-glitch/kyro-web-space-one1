import test from 'node:test';
import assert from 'node:assert/strict';

import { buildTurnChoreography, countTurnPairs } from '../js/animation/turn_choreography.js';

const layers = [
  { id: 'front_torso', name: 'Torso Front', character_id: 'hero', character_part_id: 'torso',
    tracks: { x: [{ t: 0, v: 0 }, { t: 100, v: 40 }], opacity: [{ t: 0, v: 1 }, { t: 100, v: 1 }] } },
  { id: 'profile_torso', name: 'Torso Profile', character_id: 'hero', character_part_id: 'torso',
    tracks: { opacity: [{ t: 0, v: 0 }, { t: 100, v: 1 }] } },
  { id: 'front_head', name: 'Head Front', character_id: 'hero', character_part_id: 'head', tracks: {} },
  { id: 'profile_head', name: 'Head Profile', character_id: 'hero', character_part_id: 'head', tracks: {} },
  { id: 'other_front', name: 'Other Front', character_id: 'other', character_part_id: 'torso', tracks: {} },
];

test('counts only complete front/profile pairs belonging to the selected character', () => {
  assert.equal(countTurnPairs(layers, 'hero'), 2);
  assert.equal(countTurnPairs(layers, 'other'), 0);
});

test('builds perspective yaw and crossfade keys while preserving unrelated tracks and outside keys', () => {
  const result = buildTurnChoreography(layers, 'hero', 20, 12, 120);
  assert.equal(result.pairCount, 2);
  assert.equal(result.startFrame, 20);
  assert.equal(result.middleFrame, 26);
  assert.equal(result.endFrame, 32);
  const front = result.layers.find(layer => layer.id === 'front_torso');
  const profile = result.layers.find(layer => layer.id === 'profile_torso');
  assert.deepEqual(front.tracks.rotation_y.map(key => [key.t, key.v]), [[20, 0], [26, 45], [32, 90]]);
  assert.deepEqual(front.tracks.opacity.map(key => [key.t, key.v]), [[0, 1], [20, 1], [26, 0.5], [32, 0]]);
  assert.deepEqual(profile.tracks.opacity.map(key => [key.t, key.v]), [[0, 0], [20, 0], [26, 0.5], [32, 1], [100, 1]]);
  assert.deepEqual(front.tracks.x, layers[0].tracks.x, 'unrelated tracks remain untouched');
  assert.deepEqual(layers[0].tracks.opacity, [{ t: 0, v: 1 }, { t: 100, v: 1 }], 'source project is immutable');
});

test('turn setup rejects characters without alternate pose layers and impossible ranges', () => {
  assert.throws(() => buildTurnChoreography(layers, 'other', 0, 12, 120), /matching front and profile/i);
  assert.throws(() => buildTurnChoreography(layers, 'hero', 118, 12, 120), /at least four frames/i);
});
