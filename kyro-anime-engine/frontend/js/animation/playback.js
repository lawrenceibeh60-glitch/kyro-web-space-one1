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

function tick(now) {
  if (raf === null) return;
  const { fps, duration_frames: total } = state.project.settings;
  let f = f0 + Math.floor((now - t0) / 1000 * fps);
  if (f >= total) {
    if (state.loop) f %= total;
    else { setFrame(total - 1); stop(); return; }
  }
  if (f !== state.frame) setFrame(f);
  raf = requestAnimationFrame(tick);
}

export function play() {
  if (raf !== null || !state.project) return;
  if (!state.loop && state.frame >= state.project.settings.duration_frames - 1) setFrame(0);
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
