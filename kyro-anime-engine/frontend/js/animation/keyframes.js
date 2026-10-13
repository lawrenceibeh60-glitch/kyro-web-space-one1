// frontend/js/animation/keyframes.js - pure keyframe edits on a `tracks` object ({channel: [{t,v,ease}]}).
export const TRANSFORM_CHANNELS = ['x', 'y', 'rotation', 'scale_x', 'scale_y'];
export const CHANNELS = [...TRANSFORM_CHANNELS, 'opacity'];

const byTime = (a, b) => a.t - b.t;

export function setKey(tracks, ch, t, v, ease = 'linear') {
  const tr = (tracks[ch] = tracks[ch] || []);
  const k = tr.find(o => o.t === t);
  if (k) k.v = v;
  else { tr.push({ t, v, ease }); tr.sort(byTime); }
}

export function removeKey(tracks, ch, t) {
  const tr = tracks[ch];
  if (!tr) return undefined;
  const i = tr.findIndex(k => k.t === t);
  if (i < 0) return undefined;
  const [k] = tr.splice(i, 1);
  if (!tr.length) delete tracks[ch];
  return k.v;
}

export const hasKey = (layer, ch, t) => !!layer.tracks?.[ch]?.some(k => k.t === t);

export function keyFramesOf(layer, start = Number.NEGATIVE_INFINITY, end = Number.POSITIVE_INFINITY) {
  const s = new Set();
  for (const tr of Object.values(layer.tracks || {})) {
    for (const k of tr) if (k.t >= start && k.t <= end) s.add(k.t);
  }
  return [...s].sort((a, b) => a - b);
}

// Move every channel's key at `from` to `to`; channels that already have a key at `to` are skipped.
export function moveKeys(tracks, from, to) {
  let n = 0;
  for (const tr of Object.values(tracks)) {
    const k = tr.find(o => o.t === from);
    if (k && !tr.some(o => o.t === to)) { k.t = to; tr.sort(byTime); n++; }
  }
  return n;
}

export function setEaseAt(tracks, t, ease) {
  let n = 0;
  for (const tr of Object.values(tracks)) { const k = tr.find(o => o.t === t); if (k) { k.ease = ease; n++; } }
  return n;
}
