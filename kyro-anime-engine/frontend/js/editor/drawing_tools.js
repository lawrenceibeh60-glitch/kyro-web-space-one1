// frontend/js/editor/drawing_tools.js - brush + stroke eraser. Listens to viewport pointer hooks.
import { bus } from '../core/event_bus.js';
import { state, getScene, getLayer, sceneIndex } from '../core/state_manager.js';
import { execute, batch, insertAt, removeAt, setValue } from '../core/command_manager.js';
import { findExposure, getLayerTransform } from '../rendering/renderer.js';
import { rdp, strokeHit, strokePathPoints, toLocal } from '../rendering/geometry.js';
import { toast } from '../ui/notifications.js';

let cur = null;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const r2 = v => Math.round(v * 100) / 100;
const uid = () => 's_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
const pressureOf = pt => (pt.pointerType === 'pen' ? r2(clamp(pt.pressure || 0.5, 0.05, 1)) : 1);
const SHAPE_TOOLS = new Set(['line', 'rectangle', 'ellipse', 'polygon', 'star']);
let sampleColor = () => null;

function setPreview(p) { state.preview = p; bus.emit('preview'); }

function makeStroke(points) {
  const o = state.toolOpts;
  const tool = SHAPE_TOOLS.has(cur?.tool) ? cur.tool : state.tool === 'grease' ? 'grease' : 'brush';
  const s = { id: cur?.id || uid(), tool, color: o.color, width: o.size, smoothing: o.smoothing, points };
  if (tool === 'grease') s.width = Math.max(1, (o.size || 4) * 1.3);
  if (['rectangle', 'ellipse', 'polygon', 'star'].includes(tool)) {
    s.closed = true;
    if (o.shapeFill) s.fill = o.fillColor;
  }
  if (o.opacity < 1) s.opacity = o.opacity;
  return s;
}

function shapePoints(tool, start, end) {
  if (tool === 'line') return [start, end];
  const left = Math.min(start[0], end[0]), right = Math.max(start[0], end[0]);
  const top = Math.min(start[1], end[1]), bottom = Math.max(start[1], end[1]);
  if (tool === 'rectangle') return [[left, top], [right, top], [right, bottom], [left, bottom]];
  const cx = (left + right) / 2, cy = (top + bottom) / 2;
  if (tool === 'polygon' || tool === 'star') {
    const count = tool === 'polygon' ? 6 : 10;
    return Array.from({ length: count }, (_, i) => {
      const radius = tool === 'star' && i % 2 ? 0.42 : 1;
      const angle = -Math.PI / 2 + i * Math.PI * 2 / count;
      return [cx + Math.cos(angle) * (right - left) / 2 * radius,
        cy + Math.sin(angle) * (bottom - top) / 2 * radius];
    });
  }
  return Array.from({ length: 40 }, (_, i) => {
    const angle = i * Math.PI * 2 / 40;
    return [cx + Math.cos(angle) * (right - left) / 2, cy + Math.sin(angle) * (bottom - top) / 2];
  });
}

function pointInPolygon(points, x, y) {
  let inside = false;
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const [xi, yi] = points[i], [xj, yj] = points[j];
    const intersects = (yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

function fillShape(pt) {
  const layer = getLayer(), exposure = layer && findExposure(layer, state.frame);
  if (!layer) { toast('Select a layer first', 'err'); return; }
  if (layer.locked || layer.visible === false) { toast(layer.locked ? 'Layer is locked' : 'Layer is hidden', 'err'); return; }
  if (!exposure) { toast('No drawing on this frame to fill', 'err'); return; }
  const drawing = state.project.drawings[exposure.drawing];
  if (!drawing) return;
  const transform = getLayerTransform(layer, state.frame), [x, y] = toLocal(transform, pt.x, pt.y);
  for (let index = drawing.strokes.length - 1; index >= 0; index--) {
    const stroke = drawing.strokes[index];
    const points = strokePathPoints(stroke);
    if (!stroke.closed && !stroke.commands?.some(command => command[0] === 'Z')) continue;
    if (points.length < 3 || !pointInPolygon(points, x, y)) continue;
    execute(setValue(['drawings', exposure.drawing, 'strokes', index, 'fill'], state.toolOpts.fillColor || state.toolOpts.color, 'Fill shape'));
    return;
  }
  toast('Click inside a closed shape to fill it');
}

function onDown(pt) {
  cur = null;
  const tool = state.tool;
  if (tool === 'eyedropper') {
    const color = sampleColor(pt.x, pt.y);
    if (color) { state.toolOpts.color = color; bus.emit('color:sampled', color); }
    else toast('No color at that canvas position', 'err');
    return;
  }
  if (tool === 'fill') { fillShape(pt); return; }
  if (tool !== 'brush' && tool !== 'grease' && tool !== 'eraser' && !SHAPE_TOOLS.has(tool)) return;
  const layer = getLayer();
  if (!layer) { toast('Select a layer first', 'err'); return; }
  if (layer.visible === false || layer.locked) { toast(layer.locked ? 'Layer is locked' : 'Layer is hidden', 'err'); return; }
  const t = getLayerTransform(layer, state.frame), ex = findExposure(layer, state.frame);
  cur = { tool, layer, t, ex, id: uid(), pts: [], erase: new Set(), last: null, start: null };
  if (tool === 'brush' || tool === 'grease') {
    const [x, y] = toLocal(t, pt.x, pt.y);
    cur.pts.push([r2(x), r2(y), pressureOf(pt)]);
    previewBrush();
  } else if (SHAPE_TOOLS.has(tool)) {
    const point = toLocal(t, pt.x, pt.y).map(r2);
    cur.start = point;
    cur.pts = tool === 'line' ? [point, point] : shapePoints(tool, point, point);
    previewBrush();
  } else {
    if (!ex) { cur = null; return; }
    eraseTo(pt);
  }
}

function previewBrush() {
  setPreview({ layerId: cur.layer.id, drawingId: cur.ex?.drawing, stroke: makeStroke(cur.pts), hidden: null });
}

function onMove(pt) {
  if (!cur) return;
  if (cur.tool === 'eraser') { eraseTo(pt); return; }
  if (SHAPE_TOOLS.has(cur.tool)) {
    const end = toLocal(cur.t, pt.x, pt.y).map(r2);
    cur.pts = shapePoints(cur.tool, cur.start, end);
    previewBrush();
    return;
  }
  const k = 1 - state.toolOpts.smoothing * 0.85; // stabilizer: 0 = raw input
  const last = cur.pts[cur.pts.length - 1];
  const [rx, ry] = toLocal(cur.t, pt.x, pt.y);
  const x = last[0] + (rx - last[0]) * k, y = last[1] + (ry - last[1]) * k;
  if (Math.hypot(x - last[0], y - last[1]) < 0.8 / state.view.zoom) return;
  cur.pts.push([r2(x), r2(y), r2(last[2] + (pressureOf(pt) - last[2]) * k)]);
  previewBrush();
}

function eraseTo(pt) {
  const c = cur, d = state.project.drawings[c.ex.drawing], r = state.toolOpts.eraserSize / 2;
  const dist = c.last ? Math.hypot(pt.x - c.last.x, pt.y - c.last.y) : 0;
  const steps = Math.max(1, Math.ceil(dist / (r * 0.5)));
  for (let i = 1; i <= steps; i++) {
    const q = c.last ? { x: c.last.x + (pt.x - c.last.x) * i / steps, y: c.last.y + (pt.y - c.last.y) * i / steps } : pt;
    const [lx, ly] = toLocal(c.t, q.x, q.y);
    for (const s of d.strokes) {
      if (!c.erase.has(s.id) && strokeHit(strokePathPoints(s), lx, ly, r + (s.width ?? 4) / 2)) c.erase.add(s.id);
    }
  }
  c.last = { x: pt.x, y: pt.y };
  setPreview({ layerId: c.layer.id, drawingId: c.ex.drawing, stroke: null, hidden: c.erase, cursor: { x: pt.x, y: pt.y, r } });
}

function commitBrush(c) {
  let pts = c.pts;
  if (pts.length > 2 && !SHAPE_TOOLS.has(c.tool)) pts = rdp(pts, clamp((0.4 + state.toolOpts.smoothing * 2) / state.view.zoom, 0.15, 4));
  const stroke = makeStroke(pts);
  if (c.tool === 'grease') stroke.tool = 'grease';
  const drawing = c.ex && state.project.drawings[c.ex.drawing];
  if (drawing) {
    execute(insertAt(['drawings', c.ex.drawing, 'strokes'], drawing.strokes.length, stroke, 'Draw stroke'));
    return;
  }
  // empty frame: create a drawing held until the next exposure (or end of timeline)
  const lp = ['scenes', sceneIndex(), 'layers', getScene().layers.indexOf(c.layer)];
  const dur = state.project.settings.duration_frames, f = state.frame, exps = c.layer.exposures || [];
  const next = Math.min(dur, ...exps.filter(e => e.start > f).map(e => e.start));
  let n = 1; while (('d_' + n) in state.project.drawings) n++;
  const id = 'd_' + n, cmds = [];
  if (!c.layer.exposures) cmds.push(setValue([...lp, 'exposures'], []));
  cmds.push(setValue(['drawings', id], { id, name: 'Drawing ' + n, strokes: [stroke] }));
  cmds.push(insertAt([...lp, 'exposures'], exps.filter(e => e.start < f).length,
    { start: f, length: Math.max(1, next - f), drawing: id }));
  execute(batch(cmds, 'Draw stroke'));
}

function commitErase(c) {
  if (!c.erase.size) return;
  const idx = [];
  state.project.drawings[c.ex.drawing].strokes.forEach((s, i) => { if (c.erase.has(s.id)) idx.push(i); });
  idx.reverse();
  execute(batch(idx.map(i => removeAt(['drawings', c.ex.drawing, 'strokes'], i)), 'Erase'));
}

function onUp() {
  if (!cur) return;
  const c = cur; cur = null;
  if (c.tool !== 'eraser') commitBrush(c); else commitErase(c);
  setPreview(null);
}

export function initDrawingTools(options = {}) {
  sampleColor = options.sampleColor || (() => null);
  bus.on('viewport:down', onDown);
  bus.on('viewport:move', onMove);
  bus.on('viewport:up', onUp);
  bus.on('viewport:cancel', () => { cur = null; setPreview(null); });
}
