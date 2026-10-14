import test from 'node:test';
import assert from 'node:assert/strict';

import { evaluateCamera } from '../js/animation/camera_evaluator.js';
import { writeCameraChannel, zoomCameraAtPoint } from '../js/scene/camera_controller.js';

function worldPointAtPointer(camera, point, view, settings, frame) {
  const evaluated = evaluateCamera(camera, frame);
  const px = (point.x - view.panX) / view.zoom;
  const py = (point.y - view.panY) / view.zoom;
  const dx = px - settings.width / 2 - evaluated.x;
  const dy = py - settings.height / 2 - evaluated.y;
  const radians = evaluated.rotation * Math.PI / 180;
  return {
    x: (dx * Math.cos(radians) + dy * Math.sin(radians)) / evaluated.zoom,
    y: (-dx * Math.sin(radians) + dy * Math.cos(radians)) / evaluated.zoomY,
  };
}

test('camera channel keyframes are sorted, replaced by frame, and immutable', () => {
  const camera = {
    transform: { x: 4, y: 8, scale_x: 1, scale_y: 1 },
    tracks: { x: [{ t: 0, v: 4 }, { t: 20, v: 12 }] },
  };
  const updated = writeCameraChannel(camera, 'x', 9, {
    frame: 10, autokey: true, ease: 'ease_in_out',
  });
  assert.deepEqual(updated.tracks.x.map(key => key.t), [0, 10, 20]);
  assert.equal(updated.tracks.x[1].v, 9);
  assert.equal(camera.tracks.x.length, 2);

  const replaced = writeCameraChannel(updated, 'x', 11, {
    frame: 10, autokey: true, ease: 'linear',
  });
  assert.equal(replaced.tracks.x.length, 3);
  assert.equal(replaced.tracks.x[1].v, 11);
  assert.equal(updated.tracks.x[1].v, 9);
});

test('cursor-anchored dolly preserves the project point under the pointer with rotation and nonuniform scale', () => {
  const camera = {
    transform: { x: 18, y: -9, rotation: 23, scale_x: 2, scale_y: 1.4 },
    tracks: {},
  };
  const point = { x: 510, y: 280 };
  const view = { zoom: 0.8, panX: 30, panY: 40 };
  const settings = { width: 1280, height: 720 };
  const frame = 12;
  const before = worldPointAtPointer(camera, point, view, settings, frame);
  const zoomed = zoomCameraAtPoint(camera, point, 2.7, {
    frame, view, settings, autokey: false, ease: 'ease_in_out',
  });
  const after = worldPointAtPointer(zoomed, point, view, settings, frame);

  assert.ok(Math.abs(before.x - after.x) < 1e-8, `x changed: ${before.x} -> ${after.x}`);
  assert.ok(Math.abs(before.y - after.y) < 1e-8, `y changed: ${before.y} -> ${after.y}`);
  assert.equal(zoomed.transform.scale_x, 2.7);
  assert.equal(zoomed.transform.scale_y, 2.7);
});

test('camera dolly creates matching keyframes when auto-key is enabled', () => {
  const camera = { transform: { x: 0, y: 0, scale_x: 1, scale_y: 1 }, tracks: {} };
  const zoomed = zoomCameraAtPoint(camera, { x: 400, y: 200 }, 1.8, {
    frame: 24,
    view: { zoom: 1, panX: 0, panY: 0 },
    settings: { width: 1280, height: 720 },
    autokey: true,
    ease: 'ease_in_out',
  });
  for (const channel of ['x', 'y', 'scale_x', 'scale_y']) {
    assert.deepEqual(zoomed.tracks[channel].map(key => key.t), [24]);
    assert.equal(zoomed.tracks[channel][0].ease, 'ease_in_out');
  }
  assert.deepEqual(camera.tracks, {});
});
