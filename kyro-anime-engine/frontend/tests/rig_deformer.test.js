import test from 'node:test';
import assert from 'node:assert/strict';

import { deformStrokeForRig, pathCoordinateCount } from '../js/animation/rig_deformer.js';
import { renderFrame, drawWeightOverlay } from '../js/rendering/renderer.js';

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

test('quadratic and cubic path commands deform every control point using command skin weights', () => {
  const rig = { bones: [
    { id: 'arm', name: 'Arm', pivot: { x: 0, y: 0 }, rotation: 90 },
  ] };
  const commands = [
    ['M', 10, 0],
    ['L', 20, 0],
    ['Q', 25, 5, 30, 0],
    ['C', 35, 0, 40, 5, 45, 0],
    ['Z'],
  ];
  const weights = Array.from({ length: 7 }, () => [{ bone_id: 'arm', weight: 1 }]);
  assert.equal(pathCoordinateCount(commands), 7);
  const result = deformStrokeForRig({ id: 'bezier', commands, command_skin_weights: weights }, rig, 0);
  const normalized = result.commands.map(command => command.map(value => {
    if (typeof value !== 'number') return value;
    if (Math.abs(value) < 1e-8) return 0;
    const rounded = Math.round(value * 1e8) / 1e8;
    return Math.abs(value - rounded) < 1e-8 ? rounded : value;
  }));
  assert.deepEqual(normalized, [
    ['M', 0, 10],
    ['L', 0, 20],
    ['Q', -5, 25, 0, 30],
    ['C', 0, 35, -5, 40, 0, 45],
    ['Z'],
  ]);
  assert.deepEqual(commands[0], ['M', 10, 0], 'source commands are not mutated');
});

test('path coordinates without weights stay unchanged and mixed weights preserve unbound remainder', () => {
  const rig = { bones: [
    { id: 'arm', name: 'Arm', pivot: { x: 0, y: 0 }, rotation: 90 },
  ] };
  const result = deformStrokeForRig({
    id: 'partial',
    commands: [['M', 10, 0], ['Q', 20, 0, 30, 0]],
    command_skin_weights: [
      [{ bone_id: 'arm', weight: 0.5 }],
      [{ bone_id: 'arm', weight: 1 }],
      [{ bone_id: 'arm', weight: 0.5 }],
    ],
  }, rig, 0);
  const normalized = result.commands.map(command => command.map(value => {
    if (typeof value !== 'number') return value;
    if (Math.abs(value) < 1e-8) return 0;
    const rounded = Math.round(value * 1e8) / 1e8;
    return Math.abs(value - rounded) < 1e-8 ? rounded : value;
  }));
  assert.deepEqual(normalized, [
    ['M', 5, 5],
    ['Q', 0, 20, 15, 15],
  ]);
});

test('weight overlay draws markers for every weighted Bézier control coordinate', () => {
  const markers = [];
  const context = new Proxy({
    globalAlpha: 1, globalCompositeOperation: 'source-over',
    save() {}, restore() {}, translate() {}, rotate() {}, scale() {},
    beginPath() {}, arc(x, y, radius) { markers.push({ x, y, radius, color: this.fillStyle }); },
    fill() {}, stroke() {}, setLineDash() {}, fillText() {},
  }, {
    get(target, key) {
      if (key in target) return target[key];
      return () => {};
    },
    set(target, key, value) { target[key] = value; return true; },
  });
  const project = {
    settings: { width: 320, height: 240 },
    drawings: { d: { id: 'd', strokes: [{
      id: 'curve',
      commands: [['M', 10, 0], ['Q', 20, 10, 30, 0], ['Z']],
      command_skin_weights: [
        [{ bone_id: 'arm', weight: 1 }],
        [{ bone_id: 'arm', weight: 0.5 }],
        [{ bone_id: 'arm', weight: 0 }],
      ],
    }] } },
    rigs: [{ id: 'rig', character_id: 'hero', bones: [
      { id: 'arm', name: 'Arm', character_part_id: 'arm', pivot: { x: 0, y: 0 } },
    ] }],
    scenes: [{ id: 'scene', layers: [{
      id: 'layer', character_id: 'hero', character_part_id: 'arm',
      exposures: [{ start: 0, length: 1, drawing: 'd' }],
      transform: { x: 0, y: 0, scale_x: 1, scale_y: 1 },
    }] }],
  };
  drawWeightOverlay(context, project, 'scene', 'layer', 0, 'arm', 1);
  assert.equal(markers.length, 3);
  assert.deepEqual(markers.map(({ x, y }) => [x, y]), [[10, 0], [20, 10], [30, 0]]);
  assert.notEqual(markers[0].color, markers[2].color);
});
