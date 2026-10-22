// frontend/js/animation/playback.js - time-based playback (frame follows the clock, so dropped frames don't slow it down)
import { bus } from '../core/event_bus.js';
import { state, setState } from '../core/state_manager.js';

let raf = null, t0 = 0, f0 = 0;

export const isPlaying = () => raf !== null;

export function setFrame(n) {
  if (!state.project) return;
  const max = state.project.settings.duration_frames - 1;
  setState({ frame: Math.min(max, Math.max(0, Math.round(n))) });
}

function activeRange() {
  const total = state.project?.settings?.duration_frames || 1;
  const range = state.project?.preview_range;
  if (range && Number.isInteger(range.start) && Number.isInteger(range.end)
      && range.start >= 0 && range.end >= range.start && range.end < total) {
    return { start: range.start, end: range.end };
  }
  return { start: 0, end: total - 1 };
}

function tick(now) {
  if (raf === null) return;
  const { fps } = state.project.settings;
  const range = activeRange();
  let f = f0 + Math.floor((now - t0) / 1000 * fps);
  if (f > range.end) {
    if (state.loop) f = range.start + ((f - range.start) % (range.end - range.start + 1));
    else { setFrame(range.end); stop(); return; }
  }
  if (f < range.start) f = range.start;
  if (f !== state.frame) setFrame(f);
  raf = requestAnimationFrame(tick);
}

export function play() {
  if (raf !== null || !state.project) return;
  const range = activeRange();
  if (state.frame < range.start || state.frame > range.end || (!state.loop && state.frame >= range.end)) setFrame(range.start);
  t0 = performance.now(); f0 = state.frame;
  raf = requestAnimationFrame(tick);
  bus.emit('playback', { playing: true });
}

export function stop() {
  if (raf === null) return;
  cancelAnimationFrame(raf); raf = null;
  bus.emit('playback', { playing: false });
}

export const toggle = () => (isPlaying() ? stop() : play());
