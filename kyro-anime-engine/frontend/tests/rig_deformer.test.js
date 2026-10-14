import test from 'node:test';
import assert from 'node:assert/strict';

import { deformStrokeForRig } from '../js/animation/rig_deformer.js';
import { renderFrame } from '../js/rendering/renderer.js';

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
  assert.ok(Math.abs(result.points[0][1] - 10) < 1e-8);
});

test('renderer uses weighted deformation instead of rigidly rotating a skinned stroke', () => {
  const points = [];
  const context = new Proxy({
    globalAlpha: 1,
    globalCompositeOperation: 'source-over',
    lineCap: 'round',
    lineJoin: 'round',
    lineWidth: 1,
    strokeStyle: '#000',
    fillStyle: '#fff',
    save() {}, restore() {}, beginPath() {}, rect() {}, clip() {}, fillRect() {},
    translate() {}, rotate() {}, scale() {}, moveTo(x, y) { points.push([x, y]); },
    lineTo(x, y) { points.push([x, y]); }, quadraticCurveTo() {}, bezierCurveTo() {},
    closePath() {}, stroke() {}, fill() {}, arc() {}, setLineDash() {}, fillText() {},
  }, {
    get(target, key) {
      if (key in target) return target[key];
      if (key === 'createRadialGradient') return () => ({ addColorStop() {} });
      return () => {};
    },
    set(target, key, value) { target[key] = value; return true; },
  });
  const project = {
    settings: { width: 320, height: 240, background: '#fff', duration_frames: 1 },
    drawings: { d: { id: 'd', strokes: [{
      id: 'skin', points: [[10, 0], [20, 0]], width: 1,
      skin_weights: [
        [{ bone_id: 'arm', weight: 1 }],
        [{ bone_id: 'arm', weight: 1 }],
      ],
    }] } },
    rigs: [{ id: 'rig', name: 'Rig', character_id: 'hero', bones: [
      { id: 'arm', name: 'Arm', character_part_id: 'arm', pivot: { x: 0, y: 0 }, rotation: 90 },
    ] }],
    effects: [],
    scenes: [{ id: 'scene', layers: [{
      id: 'layer', type: 'drawing', character_id: 'hero', character_part_id: 'arm',
      exposures: [{ start: 0, length: 1, drawing: 'd' }],
    }], camera: { transform: { x: 0, y: 0, scale_x: 1, scale_y: 1 }, tracks: {} } }],
  };
  renderFrame(context, project, 'scene', 0);
  assert.ok(points.some(([x, y]) => Math.abs(x) < 1e-8 && Math.abs(y - 10) < 1e-8));
  assert.ok(points.some(([x, y]) => Math.abs(x) < 1e-8 && Math.abs(y - 20) < 1e-8));
});
