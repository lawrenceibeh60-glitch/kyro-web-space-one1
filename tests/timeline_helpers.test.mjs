import test from 'node:test';
import assert from 'node:assert/strict';
import { frameFromTimelineX, previewExposureEdit, validateExposureTrack } from '../kyro-anime-engine/frontend/js/animation/timeline.js';

test('frame conversion clamps to the valid zero-based range', () => {
  assert.equal(frameFromTimelineX(16, 6, 10, 12), 1);
  assert.equal(frameFromTimelineX(-100, 6, 10, 12), 0);
  assert.equal(frameFromTimelineX(9999, 6, 10, 12), 11);
});
test('moving an exposure preserves duration and respects adjacent exposures', () => {
  assert.deepEqual(previewExposureEdit({ start: 10, length: 5, drawing: 'd_1' }, 'move', 20, { previousEnd: 4, nextStart: 24, total: 30 }), { start: 19, length: 5, drawing: 'd_1' });
});
test('resizing an exposure cannot cross neighbors or become empty', () => {
  assert.deepEqual(previewExposureEdit({ start: 10, length: 5, drawing: 'd_1' }, 'left', -50, { previousEnd: 8, nextStart: 20, total: 30 }), { start: 8, length: 7, drawing: 'd_1' });
  assert.deepEqual(previewExposureEdit({ start: 10, length: 5, drawing: 'd_1' }, 'right', 50, { previousEnd: 0, nextStart: 18, total: 30 }), { start: 10, length: 8, drawing: 'd_1' });
});
test('exposure validation rejects overlaps and out-of-range exposures', () => {
  assert.equal(validateExposureTrack([{ start: 0, length: 4, drawing: 'd_1' }, { start: 3, length: 2, drawing: 'd_2' }], 10).valid, false);
  assert.equal(validateExposureTrack([{ start: 8, length: 3, drawing: 'd_1' }], 10).valid, false);
  assert.equal(validateExposureTrack([{ start: 0, length: 4, drawing: 'd_1' }, { start: 4, length: 2, drawing: 'd_2' }], 10).valid, true);
});
