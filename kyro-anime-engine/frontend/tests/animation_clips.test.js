import test from 'node:test';
import assert from 'node:assert/strict';

import {
  blendRigRotation,
  evaluateRigAnimation,
  evaluateWalkCycle,
  inferBoneRole,
  solveTwoBoneIK,
} from '../js/animation/animation_clips.js';
import { renderFrame } from '../js/rendering/renderer.js';

test('walk clip is deterministic, cyclic, and animates opposing limbs plus body motion', () => {
  const rig = { animation: { type: 'walk', cycle_frames: 24, stride: 30, bob: 6, loop: true } };
  const first = evaluateWalkCycle(rig, 3);
  const repeated = evaluateWalkCycle(rig, 27);
  assert.deepEqual(first, { ...repeated, frame: 3 });
  assert.notEqual(first.angles.left_thigh, first.angles.right_thigh);
  assert.notEqual(first.angles.left_upper_arm, first.angles.right_upper_arm);
  assert.ok(first.rootOffset.y <= 0 && first.rootOffset.y >= -6);
  assert.equal(first.clip, 'walk');
});

test('walk clip maps named rig bones to evaluated rotations', () => {
  const rig = {
    character_id: 'hero',
    animation: { type: 'walk', cycle_frames: 24, stride: 32 },
    bones: [
      { id: 'hip_root', name: 'Pelvis', character_part_id: 'pelvis', pivot: { x: 0, y: 0 } },
      { id: 'left_thigh', name: 'Left Thigh', character_part_id: 'left_leg', pivot: { x: 0, y: 0 } },
      { id: 'right_thigh', name: 'Right Thigh', character_part_id: 'right_leg', pivot: { x: 0, y: 0 } },
    ],
  };
  const pose = evaluateRigAnimation(rig, 6);
  assert.equal(pose.clip, 'walk');
  assert.ok(Number.isFinite(pose.bones.left_thigh));
  assert.ok(Number.isFinite(pose.bones.right_thigh));
  assert.notEqual(pose.bones.left_thigh, pose.bones.right_thigh);
  assert.equal(evaluateRigAnimation({ ...rig, animation: { ...rig.animation, enabled: false } }, 6), null);
});

test('bone role inference recognises common left/right rig naming conventions', () => {
  assert.equal(inferBoneRole({ name: 'Left Upper Leg' }), 'left_thigh');
  assert.equal(inferBoneRole({ id: 'right_forearm' }), 'right_forearm');
  assert.equal(inferBoneRole({ name: 'Spine 01' }), 'torso');
});

test('two-bone IK returns finite reachable angles and clamps unreachable targets', () => {
  const solved = solveTwoBoneIK({ x: 0, y: 0 }, { x: 50, y: 0 }, 30, 30);
  assert.ok(Number.isFinite(solved.shoulder));
  assert.ok(Number.isFinite(solved.elbow));
  assert.ok(Math.abs(solved.reach - 50) < 1e-8);
  const clamped = solveTwoBoneIK({ x: 0, y: 0 }, { x: 500, y: 0 }, 30, 30);
  assert.ok(clamped.reach < 60);
  assert.throws(() => solveTwoBoneIK({ x: 0, y: 0 }, { x: 1, y: 1 }, 0, 5), TypeError);
});

test('clip rotation blends additively with authored bone animation', () => {
  assert.equal(blendRigRotation(10, 20, 0.5), 15);
  assert.equal(blendRigRotation(10, null, 1), 10);
});

test('renderer applies procedural rig motion to a real character-part layer', () => {
  const rotations = [];
  const context = new Proxy({
    globalAlpha: 1,
    globalCompositeOperation: 'source-over',
    lineCap: 'round',
    lineJoin: 'round',
    lineWidth: 1,
    strokeStyle: '#000',
    fillStyle: '#fff',
    save() {}, restore() {}, beginPath() {}, rect() {}, clip() {}, fillRect() {},
    translate() {}, rotate(value) { rotations.push(value); }, scale() {}, moveTo() {},
    lineTo() {}, quadraticCurveTo() {}, bezierCurveTo() {}, closePath() {}, stroke() {},
    fill() {}, arc() {}, setLineDash() {}, fillText() {},
  }, {
    get(target, key) {
      if (key in target) return target[key];
      if (key === 'createRadialGradient') return () => ({ addColorStop() {} });
      return () => {};
    },
    set(target, key, value) { target[key] = value; return true; },
  });
  const project = {
    settings: { width: 320, height: 240, background: '#fff', duration_frames: 24 },
    drawings: { d: { id: 'd', strokes: [{ id: 'line', points: [[10, 10], [30, 30]], width: 2 }] } },
    characters: [{ id: 'hero', name: 'Hero', format: 'kae-character', version: 1, parts: [
      { id: 'left_leg', name: 'Left leg', strokes: [{ id: 'line', points: [[10, 10], [30, 30]], width: 2 }] },
    ] }],
    rigs: [{ id: 'rig', name: 'Hero rig', character_id: 'hero', animation: { type: 'walk', cycle_frames: 24, stride: 30 }, bones: [
      { id: 'left_thigh', name: 'Left Thigh', character_part_id: 'left_leg', pivot: { x: 20, y: 20 } },
    ] }],
    effects: [],
    scenes: [{ id: 'scene', layers: [{ id: 'layer', type: 'drawing', character_id: 'hero',
      character_part_id: 'left_leg', depth: 1, exposures: [{ start: 0, length: 24, drawing: 'd' }] }],
      camera: { transform: { x: 0, y: 0, scale_x: 1, scale_y: 1 }, tracks: {} } }],
  };
  renderFrame(context, project, 'scene', 6);
  assert.ok(rotations.some(angle => Math.abs(angle) > 0.01), 'expected renderer to apply evaluated rig rotation');
});
