// Character Line Tracement + Bone Rigging interaction for KAE.
// Uses the existing viewport's project-space pointer events and native rig schema.
import { state } from '../core/state_manager.js';
import { bus } from '../core/event_bus.js';
import { execute, setValue } from '../core/command_manager.js';
import { evaluateCamera } from './camera_evaluator.js';

const $ = id => document.getElementById(id);
const clamp = (n, a, b) => Math.min(b, Math.max(a, n));
const idFor = prefix => prefix + '_' + Math.random().toString(36).slice(2, 9);
let tracing = false;
let boneRigging = false;
let start = null;
let current = null;
let overlay = null;
let overlayCtx = null;
let viewportCanvas = null;

function activeRig() {
  const rigs = state.project?.rigs || [];
  const characterId = state.activeRigCharacterId || $('rigCharacter')?.value;
  const index = rigs.findIndex(r => r.character_id === characterId);
  return index < 0 ? null : { rig: rigs[index], index };
}
function notify(message, error = false) {
  const status = $('lineTraceStatus');
  if (status) { status.textContent = message; status.style.color = error ? 'var(--kae-danger, #ff7777)' : ''; }
}
function ensureOverlay() {
  viewportCanvas = $('canvas');
  if (!viewportCanvas || overlay) return;
  const parent = viewportCanvas.parentElement;
  if (!parent) return;
  if (getComputedStyle(parent).position === 'static') parent.style.position = 'relative';
  overlay = document.createElement('canvas');
  overlay.id = 'characterLineOverlay';
  overlay.setAttribute('aria-hidden', 'true');
  Object.assign(overlay.style, { position: 'absolute', inset: '0', width: '100%', height: '100%', pointerEvents: 'none', zIndex: '3' });
  parent.append(overlay);
  overlayCtx = overlay.getContext('2d');
  const resize = () => {
    const rect = parent.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    overlay.width = Math.max(1, Math.round(rect.width * dpr));
    overlay.height = Math.max(1, Math.round(rect.height * dpr));
    overlayCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    paintOverlay();
  };
  new ResizeObserver(resize).observe(parent);
  window.addEventListener('resize', resize);
  resize();
}
function screenPoint(point) {
  if (!viewportCanvas || !state.project) return point;
  const rect = viewportCanvas.getBoundingClientRect();
  const view = state.view || { zoom: 1, panX: 0, panY: 0 };
  const scene = state.project.scenes?.find(s => s.id === state.sceneId);
  const camera = evaluateCamera(scene?.camera, state.frame);
  const layer = scene?.layers?.find(l => l.id === state.layerId);
  const depth = clamp(layer?.depth ?? 1, 0, 2);
  const zx = Math.max(.001, 1 + (camera.zoom - 1) * depth);
  const zy = Math.max(.001, 1 + (camera.zoomY - 1) * depth);
  const radians = camera.rotation * depth * Math.PI / 180;
  const x = point.x - state.project.settings.width / 2;
  const y = point.y - state.project.settings.height / 2;
  const rx = x * Math.cos(radians) - y * Math.sin(radians);
  const ry = x * Math.sin(radians) + y * Math.cos(radians);
  return {
    x: ((state.project.settings.width / 2 + camera.x * depth + rx * zx) * view.zoom + view.panX),
    y: ((state.project.settings.height / 2 + camera.y * depth + ry * zy) * view.zoom + view.panY),
  };
}
function paintOverlay() {
  if (!overlayCtx || !overlay) return;
  const rect = overlay.getBoundingClientRect();
  overlayCtx.clearRect(0, 0, rect.width, rect.height);
  if (!tracing || !start || !current) return;
  const a = screenPoint(start), b = screenPoint(current);
  overlayCtx.save();
  overlayCtx.lineWidth = 2;
  overlayCtx.strokeStyle = boneRigging ? '#e6b84c' : '#6ba9ff';
  overlayCtx.setLineDash([7, 5]);
  overlayCtx.beginPath(); overlayCtx.moveTo(a.x, a.y); overlayCtx.lineTo(b.x, b.y); overlayCtx.stroke();
  overlayCtx.setLineDash([]);
  for (const p of [a, b]) {
    overlayCtx.beginPath(); overlayCtx.arc(p.x, p.y, 5, 0, Math.PI * 2);
    overlayCtx.fillStyle = '#11151b'; overlayCtx.fill();
    overlayCtx.strokeStyle = '#ffd778'; overlayCtx.stroke();
  }
  overlayCtx.restore();
}
function parentAtStart(rig, point, excludeId = null) {
  let best = null, bestDistance = Infinity;
  for (const bone of rig.bones || []) {
    if (bone.id === excludeId || !bone.pivot) continue;
    const angle = (Number(bone.rotation) || 0) * Math.PI / 180;
    const length = Math.max(0, Number(bone.length) || 0);
    const end = { x: bone.pivot.x + Math.cos(angle) * length, y: bone.pivot.y + Math.sin(angle) * length };
    const d = Math.hypot(end.x - point.x, end.y - point.y);
    const pivotD = Math.hypot(bone.pivot.x - point.x, bone.pivot.y - point.y);
    const candidateDistance = Math.min(d, pivotD);
    if (candidateDistance < bestDistance) { bestDistance = candidateDistance; best = bone; }
  }
  return bestDistance <= 32 ? best : null;
}
function createBone(a, b) {
  const active = activeRig();
  if (!active) { notify('Create/select a character rig in Studio → Rig first.', true); return; }
  const partId = $('bonePart')?.value;
  if (!partId) { notify('Choose a Character Part in the Rig panel before drawing a bone.', true); return; }
  const dx = b.x - a.x, dy = b.y - a.y, length = Math.hypot(dx, dy);
  if (length < 3) { notify('Bone was too short. Draw a longer line.', true); return; }
  const rig = active.rig;
  const parent = parentAtStart(rig, a);
  const name = ($('boneName')?.value || 'Bone').trim().slice(0, 64) || 'Bone';
  const used = new Set((rig.bones || []).map(item => item.id));
  let id = idFor('bone');
  while (used.has(id)) id = idFor('bone');
  const bone = {
    id, name, character_part_id: partId,
    pivot: { x: clamp(a.x, -8192, 8192), y: clamp(a.y, -8192, 8192) },
    rotation: Math.atan2(dy, dx) * 180 / Math.PI,
    length: clamp(length, 0, 16384),
  };
  if (parent) bone.parent_id = parent.id;
  const next = [...(rig.bones || []), bone];
  execute(setValue(['rigs', active.index, 'bones'], next, 'Create bone from Character Line Tracement'));
  state.showRigOverlay = true;
  const show = $('showRigOverlay'); if (show) show.checked = true;
  $('boneName').value = name + ' 2';
  notify('Created ' + name + (parent ? ' and connected it to ' + parent.name + '.' : '. No nearby parent joint was found.'));
  bus.emit('project:changed', { label: 'Create bone from line' });
}
function down(point) {
  if (!tracing || !boneRigging) return;
  start = { x: point.x, y: point.y }; current = { ...start }; paintOverlay();
}
function move(point) {
  if (!tracing || !boneRigging || !start) return;
  current = { x: point.x, y: point.y }; paintOverlay();
}
function up() {
  if (!tracing || !boneRigging || !start || !current) return;
  const a = start, b = current; start = current = null; paintOverlay();
  createBone(a, b);
}
function setTracing(value) {
  tracing = !!value;
  const button = $('characterLineTrace');
  if (button) { button.classList.toggle('primary', tracing); button.setAttribute('aria-pressed', String(tracing)); }
  if (!tracing) { start = current = null; paintOverlay(); }
  document.body.classList.toggle('kae-line-tracing', tracing);
  notify(tracing ? (boneRigging ? 'Draw from a joint to the next joint to create a bone.' : 'Tracing enabled. Enable Bone Rigging to turn lines into bones.') : 'Ready.');
}
function setBoneRigging(value) {
  boneRigging = !!value;
  const button = $('boneRiggingMode');
  if (button) { button.classList.toggle('primary', boneRigging); button.setAttribute('aria-pressed', String(boneRigging)); }
  if (boneRigging) setTracing(true);
  notify(boneRigging ? 'Bone Rigging active: draw a joint-to-joint line.' : 'Bone Rigging disabled.');
}
export function initCharacterLineTools() {
  if (!$('characterLineTrace') || !$('boneRiggingMode')) return;
  ensureOverlay();
  $('characterLineTrace').addEventListener('click', () => setTracing(!tracing));
  $('boneRiggingMode').addEventListener('click', () => setBoneRigging(!boneRigging));
  $('lineTraceCancel').addEventListener('click', () => { start = current = null; paintOverlay(); notify('Line cancelled.'); });
  bus.on('viewport:down', down);
  bus.on('viewport:move', move);
  bus.on('viewport:up', up);
  bus.on('viewport:cancel', () => { start = current = null; paintOverlay(); });
  bus.on('state', () => paintOverlay());
  bus.on('project:changed', () => paintOverlay());
  notify('Select a rig and Character Part, then enable both tools.');
}
initCharacterLineTools();
