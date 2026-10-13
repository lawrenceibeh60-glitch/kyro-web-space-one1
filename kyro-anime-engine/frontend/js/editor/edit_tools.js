// frontend/js/editor/edit_tools.js - Edit mode: select and move stroke points of the active layer's current drawing.
// Tap/drag a point = move it (and the rest of the selection); drag on empty space = box select.
import { bus } from '../core/event_bus.js';
import { state, getLayer } from '../core/state_manager.js';
import { execute, batch, setValue, removeAt } from '../core/command_manager.js';
import { findExposure, getLayerTransform } from '../rendering/renderer.js';
import { flattenPath, fromLocal, toLocal } from '../rendering/geometry.js';
import { prefs } from '../ui/preferences.js';
import { toast } from '../ui/notifications.js';

const sel = new Map(); // strokeId -> Set(point index)
let drag = null;
const r2 = v => Math.round(v * 100) / 100;

function info() {
  const layer = getLayer();
  if (!layer || layer.visible === false) return null;
  const ex = findExposure(layer, state.frame), d = ex && state.project.drawings[ex.drawing];
  return d ? { layer, d, id: ex.drawing, t: getLayerTransform(layer, state.frame) } : null;
}

const count = () => { let n = 0; for (const s of sel.values()) n += s.size; return n; };
export const hasSelection = () => count() > 0;
const isSel = (sid, i) => !!sel.get(sid)?.has(i);
const strokeById = (inf, sid) => inf.d.strokes.find(s => s.id === sid);
const strokeIndex = (inf, sid) => inf.d.strokes.findIndex(s => s.id === sid);
const basePath = inf => ['drawings', inf.id, 'strokes'];
const geometryField = stroke => Array.isArray(stroke.commands) ? 'commands' : 'points';

function handles(stroke) {
  if (Array.isArray(stroke.points)) return stroke.points;
  const result = [];
  for (const command of stroke.commands || []) {
    for (let index = 1; index + 1 < command.length; index += 2) {
      result.push([command[index], command[index + 1]]);
    }
  }
  return result;
}

function cloneGeometry(value) {
  return value.map(item => Array.isArray(item) ? [...item] : item);
}

function moveHandles(field, original, selected, dx, dy) {
  if (field === 'points') {
    return original.map((point, index) => (
      selected.has(index)
        ? [r2(point[0] + dx), r2(point[1] + dy), ...point.slice(2)]
        : point
    ));
  }
  let handleIndex = 0;
  return original.map(command => {
    if (command[0] === 'Z') return command;
    const moved = [...command];
    for (let index = 1; index + 1 < command.length; index += 2) {
      if (selected.has(handleIndex)) {
        moved[index] = r2(command[index] + dx);
        moved[index + 1] = r2(command[index + 1] + dy);
      }
      handleIndex++;
    }
    return moved;
  });
}

function ready(inf) {
  if (!inf) { toast('Nothing to edit on this frame', 'err'); return false; }
  if (inf.layer.locked) { toast('Layer is locked', 'err'); return false; }
  return true;
}

function hit(inf, pt) {
  const r = (prefs.handle * 1.8) / state.view.zoom;
  let best = null, bd = r;
  for (const s of inf.d.strokes) {
    handles(s).forEach((p, i) => {
      const [wx, wy] = fromLocal(inf.t, p[0], p[1]);
      const d = Math.hypot(wx - pt.x, wy - pt.y);
      if (d <= bd) { bd = d; best = { sid: s.id, i }; }
    });
  }
  return best;
}

function onDown(pt) {
  drag = null;
  if (state.tool !== 'edit') return;
  const inf = info();
  if (!ready(inf)) return;
  const h = hit(inf, pt);
  if (h) {
    if (!isSel(h.sid, h.i)) { sel.clear(); sel.set(h.sid, new Set([h.i])); }
    const before = new Map();
    for (const sid of sel.keys()) {
      const stroke = strokeById(inf, sid), field = geometryField(stroke);
      before.set(sid, { field, value: cloneGeometry(stroke[field]) });
    }
    drag = { mode: 'move', inf, start: pt, before };
  } else {
    sel.clear();
    drag = { mode: 'box', inf, start: pt, cur: pt };
  }
  bus.emit('preview');
}

function onMove(pt) {
  if (!drag) return;
  const { inf } = drag;
  if (drag.mode === 'move') {
    const [ax, ay] = toLocal(inf.t, drag.start.x, drag.start.y), [bx, by] = toLocal(inf.t, pt.x, pt.y);
    const dx = bx - ax, dy = by - ay;
    for (const [sid, original] of drag.before) {
      const set = sel.get(sid);
      strokeById(inf, sid)[original.field] = moveHandles(original.field, original.value, set, dx, dy);
    }
  } else {
    drag.cur = pt;
    const x0 = Math.min(drag.start.x, pt.x), x1 = Math.max(drag.start.x, pt.x);
    const y0 = Math.min(drag.start.y, pt.y), y1 = Math.max(drag.start.y, pt.y);
    sel.clear();
    for (const s of inf.d.strokes) {
      handles(s).forEach((p, i) => {
        const [wx, wy] = fromLocal(inf.t, p[0], p[1]);
        if (wx >= x0 && wx <= x1 && wy >= y0 && wy <= y1) { if (!sel.has(s.id)) sel.set(s.id, new Set()); sel.get(s.id).add(i); }
      });
    }
  }
  bus.emit('preview');
}

function onUp() {
  if (!drag) return;
  const d = drag; drag = null;
  if (d.mode === 'move') {
    const cmds = [];
    for (const [sid, original] of d.before) {
      const s = strokeById(d.inf, sid), after = s[original.field];
      s[original.field] = original.value;
      if (JSON.stringify(after) !== JSON.stringify(original.value)) {
        cmds.push(setValue([...basePath(d.inf), strokeIndex(d.inf, sid), original.field], after));
      }
    }
    if (cmds.length) execute(batch(cmds, 'Move points'));
  }
  bus.emit('preview');
}

function cancel() {
  if (!drag) return;
  if (drag.mode === 'move') {
    for (const [sid, original] of drag.before) {
      strokeById(drag.inf, sid)[original.field] = original.value;
    }
  }
  drag = null; bus.emit('preview');
}

function prune() {
  const inf = info();
  for (const [sid, set] of [...sel]) {
    const s = inf && strokeById(inf, sid);
    if (!s) { sel.delete(sid); continue; }
    for (const i of [...set]) if (i >= handles(s).length) set.delete(i);
    if (!set.size) sel.delete(sid);
  }
}

export function selectAll() {
  const inf = info(); if (!inf) return;
  const total = inf.d.strokes.reduce((n, s) => n + handles(s).length, 0);
  const all = total > 0 && count() === total;
  sel.clear();
  if (!all) for (const s of inf.d.strokes) sel.set(s.id, new Set(handles(s).map((_, i) => i)));
  bus.emit('preview');
}

export function deleteSelected() {
  const inf = info();
  if (!hasSelection() || !ready(inf)) return;
  const sets = [], removes = [];
  inf.d.strokes.forEach((s, idx) => {
    const set = sel.get(s.id);
    if (!set || !set.size) return;
    if (Array.isArray(s.commands)) {
      removes.push(idx);
      return;
    }
    const rest = s.points.filter((_, i) => !set.has(i));
    if (rest.length) sets.push(setValue([...basePath(inf), idx, 'points'], rest));
    else removes.push(idx);
  });
  removes.sort((a, b) => b - a);
  execute(batch([...sets, ...removes.map(i => removeAt(basePath(inf), i))], 'Delete points'));
  sel.clear(); bus.emit('preview');
}

export function smoothSelected() {
  const inf = info();
  if (!hasSelection() || !ready(inf)) return;
  const cmds = [];
  inf.d.strokes.forEach((s, idx) => {
    const set = sel.get(s.id); if (!set) return;
    if (!Array.isArray(s.points)) return;
    const n = s.points.length, P = s.points;
    const out = P.map((p, i) => {
      if (!set.has(i) || n < 3) return p;
      if (!s.closed && (i === 0 || i === n - 1)) return p;
      const a = P[(i - 1 + n) % n], b = P[(i + 1) % n];
      return [r2(p[0] * 0.5 + (a[0] + b[0]) * 0.25), r2(p[1] * 0.5 + (a[1] + b[1]) * 0.25), ...p.slice(2)];
    });
    if (JSON.stringify(out) !== JSON.stringify(P)) cmds.push(setValue([...basePath(inf), idx, 'points'], out));
  });
  if (cmds.length) execute(batch(cmds, 'Smooth points'));
}

// Called by the viewport after the frame is drawn (world coordinates, view transform active).
export function drawEditOverlay(ctx, zoom) {
  const inf = info(); if (!inf) return;
  ctx.save();
  ctx.lineWidth = 1 / zoom; ctx.strokeStyle = 'rgba(74,144,226,.55)';
  for (const s of inf.d.strokes) {
    if (Array.isArray(s.commands)) {
      const transformed = s.commands.map(command => {
        if (command[0] === 'Z') return command;
        const mapped = [command[0]];
        for (let index = 1; index + 1 < command.length; index += 2) {
          mapped.push(...fromLocal(inf.t, command[index], command[index + 1]));
        }
        return mapped;
      });
      ctx.beginPath();
      for (const [kind, ...coords] of transformed) {
        if (kind === 'M') ctx.moveTo(...coords);
        else if (kind === 'L') ctx.lineTo(...coords);
        else if (kind === 'Q') ctx.quadraticCurveTo(...coords);
        else if (kind === 'C') ctx.bezierCurveTo(...coords);
        else if (kind === 'Z') ctx.closePath();
      }
      ctx.stroke();
      continue;
    }
    ctx.beginPath();
    s.points.forEach((p, i) => { const [x, y] = fromLocal(inf.t, p[0], p[1]); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
    ctx.stroke();
  }
  const r = prefs.handle / zoom;
  for (const s of inf.d.strokes) {
    handles(s).forEach((p, i) => {
      const [x, y] = fromLocal(inf.t, p[0], p[1]);
      ctx.fillStyle = isSel(s.id, i) ? '#e87d0d' : '#ffffff';
      ctx.fillRect(x - r / 2, y - r / 2, r, r);
      ctx.strokeStyle = '#111'; ctx.strokeRect(x - r / 2, y - r / 2, r, r);
    });
  }
  if (drag?.mode === 'box') {
    ctx.setLineDash([6 / zoom, 4 / zoom]); ctx.strokeStyle = '#4a90e2'; ctx.lineWidth = 1.5 / zoom;
    ctx.strokeRect(drag.start.x, drag.start.y, drag.cur.x - drag.start.x, drag.cur.y - drag.start.y);
  }
  ctx.restore();
}

export function initEditTools() {
  bus.on('viewport:down', onDown);
  bus.on('viewport:move', onMove);
  bus.on('viewport:up', onUp);
  bus.on('viewport:cancel', cancel);
  bus.on('state', p => { if ('frame' in p || 'layerId' in p || 'tool' in p) { sel.clear(); drag = null; bus.emit('preview'); } });
  bus.on('project:changed', () => { prune(); bus.emit('preview'); });
}
