import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { renderFrame } from '../js/rendering/renderer.js';

const fixture = JSON.parse(await readFile(new URL('../../examples/rigged-arm-idle.kae', import.meta.url), 'utf8'));

function makeContext() {
  const rotations = [];
  const ctx = new Proxy({
    globalAlpha: 1, globalCompositeOperation: 'source-over', lineCap: 'round',
    lineJoin: 'round', lineWidth: 1, strokeStyle: '#000', fillStyle: '#fff',
    save() {}, restore() {}, beginPath() {}, rect() {}, clip() {}, fillRect() {},
    translate() {}, rotate(value) { rotations.push(value); }, scale() {}, moveTo() {},
    lineTo() {}, quadraticCurveTo() {}, bezierCurveTo() {}, closePath() {},
    stroke() {}, fill() {}, arc() {}, setLineDash() {}, fillText() {},
  }, {
    get(target, key) {
      if (key in target) return target[key];
      if (key === 'createRadialGradient') return () => ({ addColorStop() {} });
      return () => {};
    },
    set(target, key, value) { target[key] = value; return true; },
  });
  return { ctx, rotations };
}

function renderRotations(project, frame) {
  const { ctx, rotations } = makeContext();
  renderFrame(ctx, project, 'test_scene', frame);
  return rotations;
}

test('real KAE rig fixture renders distinct arm poses from native bone keyframes', () => {
  const start = renderRotations(fixture, 0);
  const middle = renderRotations(fixture, 6);
  const peak = renderRotations(fixture, 12);
  const loopEnd = renderRotations(fixture, 23);
  assert.ok(start.some(angle => Math.abs(angle) > 0.01), 'start pose should rotate the arm');
  assert.notDeepEqual(middle, start, 'intermediate pose must differ from the start pose');
  assert.notDeepEqual(peak, middle, 'keyframe pose must differ from the intermediate pose');
  assert.deepEqual(loopEnd, start, 'final keyed pose should return to the start pose for looping');
});

test('the test animation survives a KAE JSON save/reopen round-trip', () => {
  const reopened = JSON.parse(JSON.stringify(fixture));
  assert.equal(reopened.format, 'kae');
  assert.equal(reopened.settings.fps, 24);
  assert.equal(reopened.rigs[0].bones.find(bone => bone.id === 'upper_arm_bone').tracks.rotation[1].v, 35);
  assert.deepEqual(renderRotations(reopened, 12), renderRotations(fixture, 12));
});

test('the rigged animation uses project layers, drawings, bone-parent links, and frame exposures', () => {
  assert.equal(fixture.scenes[0].layers.length, 3);
  assert.equal(fixture.drawings.upper_arm.strokes.length, 1);
  assert.equal(fixture.rigs[0].bones.find(bone => bone.id === 'forearm_bone').parent_id, 'upper_arm_bone');
  for (const layer of fixture.scenes[0].layers) {
    assert.equal(layer.exposures[0].start, 0);
    assert.equal(layer.exposures[0].length, 24);
    assert.ok(fixture.drawings[layer.exposures[0].drawing]);
  }
});
