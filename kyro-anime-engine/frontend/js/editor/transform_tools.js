// frontend/js/editor/transform_tools.js - Object mode: move / rotate / scale a layer, keyframing, origin.
// Every edit mutates a layer, snapshots it, reverts, then executes one undoable animPatch command.
import { bus } from '../core/event_bus.js';
import { state } from '../core/state_manager.js';
import { getLayer } from '../core/state_manager.js';
import { execute, animPatch, findLayer, snapshotLayer, restoreLayer } from '../core/command_manager.js';
import { evaluateTransform, evaluateOpacity } from '../animation/pose_evaluator.js';
import * as K from '../animation/keyframes.js';
import { setFrame } from '../animation/playback.js';
import { findExposure } from '../rendering/renderer.js';
import { strokePathPoints } from '../rendering/geometry.js';
import { toast } from '../ui/notifications.js';

const r3 = v => Math.round(v * 1000) / 1000;
const sameState = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function usable(layer) {
  if (!layer) { toast('Select a layer first', 'err'); return false; }
  if (layer.locked) { toast('Layer is locked', 'err'); return false; }
  return true;
}

function editLayer(layer, mutate, label) {
  const before = snapshotLayer(layer);
  mutate(layer);
  const after = snapshotLayer(layer);
  restoreLayer(layer, before);
  if (sameState(before, after)) return false;
  execute(animPatch(layer.id, after, label));
  return true;
}

function shouldAutoKey(layer, ch, frame = state.frame) {
  if (!layer) return false;
  if (state.autokey) return true;
  const tr = layer.tracks?.[ch];
  return Array.isArray(tr) && tr.some(k => k.t === frame);
}

// Animated channel (or auto-key on) -> key at the current frame; otherwise change the static value.
function setChannel(layer, ch, v, frame = state.frame) {
  if (shouldAutoKey(layer, ch, frame)) {
    layer.tracks = layer.tracks || {};
    K.setKey(layer.tracks, ch, frame, v, state.keyEase);
  } else if (ch === 'opacity') layer.opacity = v;
  else { layer.transform = layer.transform || {}; layer.transform[ch] = v; }
}

// Remove keys at frame t (only channels in `only`, or all). A channel that loses its last key keeps its value.
function removeKeys(layer, t, only) {
  if (!layer.tracks) return;
  const ev = evaluateTransform(layer, t), eo = evaluateOpacity(layer, t);
  for (const ch of only || Object.keys(layer.tracks)) {
    if (!K.hasKey(layer, ch, t)) continue;
    K.removeKey(layer.tracks, ch, t);
    if (!layer.tracks[ch]) {
      if (ch === 'opacity') layer.opacity = eo;
      else { layer.transform = layer.transform || {}; layer.transform[ch] = ev[ch]; }
    }
  }
  if (!Object.keys(layer.tracks).length) delete layer.tracks;
}

const valueOf = (layer, ch, f) => (ch === 'opacity' ? evaluateOpacity(layer, f) : evaluateTransform(layer, f)[ch]);

// ---------- property-field / button operations ----------
export function setField(ch, v) {
  const layer = getLayer(); if (!usable(layer) || !Number.isFinite(v)) return;
  if (ch === 'opacity') v = Math.min(1, Math.max(0, v));
  editLayer(layer, l => setChannel(l, ch, v), 'Edit ' + ch);
}

export function toggleKey(ch) {
  const layer = getLayer(); if (!usable(layer)) return;
  const f = state.frame;
  editLayer(layer, l => {
    if (K.hasKey(l, ch, f)) removeKeys(l, f, [ch]);
    else { l.tracks = l.tracks || {}; K.setKey(l.tracks, ch, f, valueOf(l, ch, f), state.keyEase); }
  }, 'Toggle key');
}

export function keyAll() {
  const layer = getLayer(); if (!usable(layer)) return;
  const f = state.frame, ev = evaluateTransform(layer, f);
  editLayer(layer, l => {
    l.tracks = l.tracks || {};
    for (const ch of K.TRANSFORM_CHANNELS) K.setKey(l.tracks, ch, f, ev[ch], state.keyEase);
  }, 'Insert keys');
}

export function unkeyAll() {
  const layer = getLayer(); if (!usable(layer)) return;
  editLayer(layer, l => removeKeys(l, state.frame, null), 'Delete keys');
}

export function deleteSelectedKey() {
  const s = state.selKey; if (!s) return;
  const layer = findLayer(s.layerId);
  if (layer && usable(layer)) editLayer(layer, l => removeKeys(l, s.frame, null), 'Delete keys');
  state.selKey = null; bus.emit('selection', {});
}

export function moveKeysCmd(layerId, from, to) {
  const layer = findLayer(layerId); if (!layer || !usable(layer)) return false;
  return editLayer(layer, l => { if (l.tracks) K.moveKeys(l.tracks, from, to); }, 'Move keys');
}

export function setEase(ease) {
  state.keyEase = ease;
  const layer = getLayer(); if (!layer || layer.locked) return;
  editLayer(layer, l => { if (l.tracks) K.setEaseAt(l.tracks, state.frame, ease); }, 'Key ease');
}

export function jumpKey(dir) {
  const layer = getLayer(); if (!layer) return;
  const frames = K.keyFramesOf(layer), f = state.frame;
  const target = dir > 0 ? frames.find(t => t > f) : [...frames].reverse().find(t => t < f);
  if (target !== undefined) setFrame(target);
}

// Move the layer origin (pivot) to the centre of the current frame's drawing without moving the art.
export function originToCenter() {
  const layer = getLayer(); if (!usable(layer)) return;
  const ex = findExposure(layer, state.frame), d = ex && state.project.drawings[ex.drawing];
  if (!d || !d.strokes.length) { toast('Nothing drawn on this frame', 'err'); return; }
  if (K.TRANSFORM_CHANNELS.some(ch => layer.tracks?.[ch])) { toast("Origin can't change on an animated transform", 'err'); return; }
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const s of d.strokes) for (const p of strokePathPoints(s)) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, t = evaluateTransform(layer, state.frame);
  const th = t.rotation * Math.PI / 180, c = Math.cos(th), s = Math.sin(th);
  const sx = t.scale_x * (cx - t.anchor_x), sy = t.scale_y * (cy - t.anchor_y);
  editLayer(layer, l => {
    l.transform = l.transform || {};
    Object.assign(l.transform, { x: r3(t.x + c * sx - s * sy), y: r3(t.y + s * sx + c * sy), anchor_x: r3(cx), anchor_y: r3(cy) });
  }, 'Set origin');
}

// ---------- viewport drag tools ----------
let drag = null;
const TOOLS = ['move', 'rotate', 'scale'];

function onDown(pt) {
  drag = null;
  if (!TOOLS.includes(state.tool)) return;
  const layer = getLayer(); if (!usable(layer)) return;
  if (layer.visible === false) { toast('Layer is hidden', 'err'); return; }
  const ev = evaluateTransform(layer, state.frame), pivot = { x: ev.x, y: ev.y };
  drag = {
    tool: state.tool, layerId: layer.id, before: snapshotLayer(layer), start: pt, ev, pivot,
    lastA: Math.atan2(pt.y - pivot.y, pt.x - pivot.x), acc: 0,
  };
}

function onMove(pt) {
  if (!drag) return;
  const layer = findLayer(drag.layerId);
  restoreLayer(layer, drag.before);
  const { tool, start, ev, pivot } = drag;
  if (tool === 'move') {
    setChannel(layer, 'x', r3(ev.x + pt.x - start.x));
    setChannel(layer, 'y', r3(ev.y + pt.y - start.y));
  } else {
    const d0 = Math.hypot(start.x - pivot.x, start.y - pivot.y);
    if (d0 >= 4 / state.view.zoom) {
      if (tool === 'rotate') {
        const a = Math.atan2(pt.y - pivot.y, pt.x - pivot.x), d = a - drag.lastA;
        drag.acc += Math.atan2(Math.sin(d), Math.cos(d)); drag.lastA = a; // unwrap across +-180
        setChannel(layer, 'rotation', r3(ev.rotation + drag.acc * 180 / Math.PI));
      } else {
        const k = Math.hypot(pt.x - pivot.x, pt.y - pivot.y) / d0;
        setChannel(layer, 'scale_x', r3(ev.scale_x * k));
        setChannel(layer, 'scale_y', r3(ev.scale_y * k));
      }
    }
  }
  bus.emit('preview');
}

function onUp() {
  if (!drag) return;
  const d = drag; drag = null;
  const layer = findLayer(d.layerId), after = snapshotLayer(layer);
  restoreLayer(layer, d.before);
  if (!sameState(after, d.before)) execute(animPatch(d.layerId, after, 'Transform ' + d.tool));
  else bus.emit('preview');
}

export function initTransformTools() {
  bus.on('viewport:down', onDown);
  bus.on('viewport:move', onMove);
  bus.on('viewport:up', onUp);
  bus.on('viewport:cancel', () => {
    if (!drag) return;
    restoreLayer(findLayer(drag.layerId), drag.before); drag = null; bus.emit('preview');
  });
}
