// frontend/js/editor/editor_controller.js - editor entry point: load, UI wiring, save.
import { Projects } from '../api/projects.js';
import { bus } from '../core/event_bus.js';
import { state, setState, getScene, getLayer, sceneIndex } from '../core/state_manager.js';
import { history } from '../core/undo_redo.js';
import { execute, undo, redo, setValue, insertAt, removeAt, batch, animPatch, snapshotLayer } from '../core/command_manager.js';
import { selectLayer } from '../core/selection_manager.js';
import { initShortcuts } from '../core/keyboard_shortcuts.js';
import { evaluateTransform, evaluateOpacity } from '../animation/pose_evaluator.js';
import { toggle as togglePlay, stop as stopPlay, isPlaying, setFrame } from '../animation/playback.js';
import { initViewport } from './viewport_controller.js';
import { initDrawingTools } from './drawing_tools.js';
import {
  initTransformTools, setField, toggleKey, keyAll, unkeyAll, deleteSelectedKey, originToCenter, setEase, jumpKey,
} from './transform_tools.js';
import { initTimelinePanel } from '../ui/timeline_panel.js';
import { initGraphEditor } from '../animation/graph_editor.js';
import { initGeometryNodes } from '../animation/geometry_nodes.js';
import { initAudioPlayback } from '../animation/audio_playback.js';
import { initEditTools, selectAll, deleteSelected, smoothSelected, hasSelection } from './edit_tools.js';
import { initWorkspaceLayout } from './workspace_layout.js';
import { initPropertiesPanel } from '../ui/properties_panel.js';
import { initHistoryPanel } from '../ui/history_panel.js';
import { initPreferences } from '../ui/preferences.js';
import { initExportDialog } from '../ui/export_dialog.js';
import { initColorPicker } from '../ui/color_picker.js';
import { initAssetBrowser } from '../ui/asset_browser.js';
import { initStudioPanel } from '../ui/studio_panel.js';
import { svg, setIcon, hydrate } from '../ui/icons.js';
import { toast } from '../ui/notifications.js';

const $ = id => document.getElementById(id);
const TOOL_NAMES = { pan: 'Hand', camera: 'Camera', brush: 'Brush', grease: 'Grease Pencil', eraser: 'Eraser', edit: 'Edit', weight: 'Weight Paint', line: 'Line', rectangle: 'Rectangle', ellipse: 'Ellipse', polygon: 'Polygon', star: 'Star', fill: 'Fill', eyedropper: 'Eyedropper', move: 'Move', rotate: 'Rotate', scale: 'Scale' };
let prevTool = 'brush';
const SLIDERS = [['optSize', 'size', 1], ['optOpacity', 'opacity', 100], ['optSmooth', 'smoothing', 100], ['optEraser', 'eraserSize', 1]];
const FIELDS = ['x', 'y', 'rotation', 'rotation_y', 'scale_x', 'scale_y', 'opacity'];
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
let viewport;
let colorPicker;

function setTool(t) {
  state.preview = null;
  setState({ tool: t });
  document.querySelectorAll('.tool').forEach(b => b.classList.toggle('active', b.dataset.tool === t));
  document.querySelectorAll('[data-tools]').forEach(g => { g.hidden = !g.dataset.tools.split(' ').includes(t); });
  if (t === 'grease') {
    const preset = state.toolOpts.greasePreset || 'pencil';
    state.toolOpts.greasePreset = preset;
    document.querySelectorAll('.gp-preset').forEach(btn => btn.classList.toggle('on', btn.dataset.gpPreset === preset));
  }
  updateUI();
}

function syncOpts() {
  for (const [id, key, k] of SLIDERS) { $(id).value = Math.round(state.toolOpts[key] * k); $(id + 'V').textContent = $(id).value; }
  $('toolColor').value = state.toolOpts.color;
  colorPicker?.setColor(state.toolOpts.color);
  document.querySelectorAll('.gp-preset').forEach(btn => btn.classList.toggle('on', btn.dataset.gpPreset === state.toolOpts.greasePreset));
}

function bumpSize(d) {
  const o = state.toolOpts;
  if (state.tool === 'eraser') o.eraserSize = clamp(o.eraserSize + d * 4, 4, 120);
  else o.size = clamp(o.size + d, 1, 80);
  syncOpts();
}

function renderSwatches() {
  const box = $('swatches'); box.innerHTML = '';
  for (const c of state.project.palette || []) {
    const b = document.createElement('button');
    b.className = 'sw'; b.style.background = c; b.title = c;
    b.setAttribute('aria-label', `Set brush color ${c}`);
    b.onclick = () => { state.toolOpts.color = c.slice(0, 7); syncOpts(); };
    b.oncontextmenu = e => {
      e.preventDefault();
      const palette = state.project.palette || [];
      execute(setValue(['palette'], palette.filter((_, i) => i !== [...box.children].indexOf(b)), 'Remove palette color'));
    };
    box.append(b);
  }
}

function addPaletteColor() {
  const color = state.toolOpts.color.toLowerCase();
  const palette = state.project.palette || [];
  if (palette.some(item => item.toLowerCase() === color)) { toast('Color is already in the palette'); return; }
  execute(setValue(['palette'], [...palette, color], 'Add palette color'));
}

function renderLayers() {
  const ul = $('layers'), sc = getScene();
  ul.innerHTML = '';
  $('duplicateLayer').disabled = !getLayer();
  $('deleteLayer').disabled = !getLayer();
  if (!sc) return;
  for (const l of [...sc.layers].reverse()) {
    const li = document.createElement('li');
    li.className = 'layer' + (l.id === state.layerId ? ' active' : '');
    const eye = document.createElement('button');
    eye.innerHTML = svg(l.visible === false ? 'eye-off' : 'eye'); eye.title = 'Visibility';
    eye.onclick = ev => { ev.stopPropagation(); toggleFlag(l.id, 'visible', l.visible === false); };
    const lock = document.createElement('button');
    lock.innerHTML = svg(l.locked ? 'lock' : 'unlock'); lock.title = 'Lock';
    lock.onclick = ev => { ev.stopPropagation(); toggleFlag(l.id, 'locked', !l.locked); };
    const name = document.createElement('span');
    name.className = 'nm'; name.textContent = l.name || l.id;
    name.title = 'Double-click or press F2 to rename';
    li.append(eye, lock, name);
    li.onclick = () => selectLayer(l.id);
    li.ondblclick = e => { e.preventDefault(); e.stopPropagation(); renameLayer(l.id); };
    ul.append(li);
  }
}

function toggleFlag(id, key, value) {
  const si = sceneIndex(), li = getScene().layers.findIndex(l => l.id === id);
  execute(setValue(['scenes', si, 'layers', li, key], value, 'Toggle ' + key));
}

function addLayer() {
  const ids = new Set(state.project.scenes.flatMap(s => s.layers.map(l => l.id)));
  let n = 1; while (ids.has('layer_' + n)) n++;
  const layer = { id: 'layer_' + n, name: 'Layer ' + n, type: 'drawing', exposures: [] };
  execute(insertAt(['scenes', sceneIndex(), 'layers'], getScene().layers.length, layer, 'Add layer'));
  selectLayer(layer.id);
}

function layerIndex(id = state.layerId) { return getScene()?.layers.findIndex(layer => layer.id === id) ?? -1; }

function renameLayer(id = state.layerId) {
  const layer = getLayer(id);
  if (!layer) return;
  const name = prompt('Rename layer', layer.name || layer.id);
  if (!name || !name.trim() || name.trim() === layer.name) return;
  execute(setValue(['scenes', sceneIndex(), 'layers', layerIndex(id), 'name'], name.trim(), 'Rename layer'));
}

function duplicateLayer() {
  const source = getLayer(), index = layerIndex();
  if (!source || index < 0) return;
  const usedLayerIds = new Set(state.project.scenes.flatMap(scene => scene.layers.map(layer => layer.id)));
  let layerNumber = 1;
  while (usedLayerIds.has('layer_' + layerNumber)) layerNumber++;
  const copy = JSON.parse(JSON.stringify(source));
  copy.id = 'layer_' + layerNumber;
  copy.name = `${source.name || 'Layer'} Copy`;
  const commands = [];
  const usedDrawingIds = new Set(Object.keys(state.project.drawings));
  let drawingNumber = 1;

  for (const exposure of copy.exposures || []) {
    const drawing = state.project.drawings[exposure.drawing];
    if (!drawing) continue;
    while (usedDrawingIds.has('d_' + drawingNumber)) drawingNumber++;
    const drawingId = 'd_' + drawingNumber;
    usedDrawingIds.add(drawingId);
    drawingNumber++;
    const drawingCopy = JSON.parse(JSON.stringify(drawing));
    drawingCopy.id = drawingId;
    exposure.drawing = drawingId;
    commands.push(setValue(['drawings', drawingId], drawingCopy, 'Duplicate drawing'));
  }

  commands.push(insertAt(['scenes', sceneIndex(), 'layers'], index + 1, copy, 'Duplicate layer'));
  execute(batch(commands, 'Duplicate layer'));
  selectLayer(copy.id);
}

function deleteLayer() {
  const index = layerIndex();
  const layer = getLayer();
  if (index < 0 || !layer || !confirm(`Delete layer "${layer.name || layer.id}"?`)) return;
  execute(removeAt(['scenes', sceneIndex(), 'layers'], index, 'Delete layer'));
}

function createQuickAnimation(channel) {
  const layer = getLayer();
  if (!layer || layer.locked) { toast(layer?.locked ? 'Layer is locked' : 'Select a layer first', 'err'); return; }
  const endFrame = state.project.settings.duration_frames - 1;
  if (endFrame < 1) { toast('Set the timeline to at least 2 frames first', 'err'); return; }
  const after = snapshotLayer(layer);
  after.tracks = after.tracks || {};
  if (channel === 'x') {
    const start = evaluateTransform(layer, 0).x;
    const travel = Math.max(80, state.project.settings.width * 0.25);
    after.tracks.x = [
      { t: 0, v: start, ease: 'ease_in_out' },
      { t: endFrame, v: start + travel, ease: 'ease_in_out' },
    ];
  } else {
    const endOpacity = evaluateOpacity(layer, endFrame);
    after.tracks.opacity = [
      { t: 0, v: 0, ease: 'ease_in_out' },
      { t: endFrame, v: endOpacity, ease: 'ease_in_out' },
    ];
  }
  execute(animPatch(layer.id, after, channel === 'x' ? 'Create motion' : 'Create fade'));
  if (isPlaying()) stopPlay();
  setFrame(0);
  togglePlay();
  toast(channel === 'x' ? 'Motion created - playing preview' : 'Fade created - playing preview', 'ok');
}

function updateFields() {
  const l = getLayer();
  const t = l ? evaluateTransform(l, state.frame) : null, op = l ? evaluateOpacity(l, state.frame) : 1;
  for (const ch of FIELDS) {
    const el = $('f_' + ch);
    el.disabled = !l;
    if (l && document.activeElement !== el) el.value = String(Math.round((ch === 'opacity' ? op : t[ch]) * 1000) / 1000);
  }
  document.querySelectorAll('.key').forEach(b => {
    const tr = l?.tracks?.[b.dataset.ch], keyed = !!tr?.some(k => k.t === state.frame);
    setIcon(b, keyed ? 'diamond-fill' : 'diamond');
    b.classList.toggle('anim', !!tr); b.disabled = !l;
  });
}

function updateUI() {
  const p = state.project; if (!p) return;
  const l = getLayer(), total = p.settings.duration_frames;
  $('projName').textContent = p.name;
  $('dirty').hidden = !state.dirty;
  $('undo').disabled = !history.canUndo;
  $('redo').disabled = !history.canRedo;
  $('fit').textContent = Math.round(state.view.zoom * 100) + '%';
  $('frameReadout').textContent = `F ${String(state.frame + 1).padStart(3, '0')}`;
  $('canvasReadout').textContent = `${p.settings.width} × ${p.settings.height}`;
  setIcon($('play'), isPlaying() ? 'pause' : 'play');
  if (document.activeElement !== $('frameNum')) $('frameNum').value = state.frame + 1;
  if (document.activeElement !== $('endFrame')) $('endFrame').value = total;
  $('loop').classList.toggle('on', state.loop);
  $('autokey').classList.toggle('on', state.autokey);
  $('keyEase').value = state.keyEase;
  $('statusTool').textContent = `${TOOL_NAMES[state.tool]}${l ? ' \u00B7 ' + (l.name || l.id) : ''}`;
  updateFields();
}

async function save(opts) {
  const silent = opts?.silent === true;
  if (!state.dirty) { if (!silent) toast('Nothing to save'); return; }
  try {
    const saved = await Projects.save(state.projectId, state.project);
    state.project.modified = saved.modified;
    setState({ dirty: false });
    if (!silent) toast('Saved', 'ok');
  } catch (e) {
    toast(e.message + (e.details?.length ? ': ' + e.details.slice(0, 3).join('; ') : ''), 'err', 6000);
  }
}

function rename() {
  const v = prompt('Project name', state.project.name);
  if (v && v.trim() && v.trim() !== state.project.name) execute(setValue(['name'], v.trim(), 'Rename'));
}

async function boot() {
  hydrate();
  colorPicker = initColorPicker({
    canvas: $('colorWheel'), valueInput: $('colorValue'), colorInput: $('toolColor'),
    valueText: $('colorValueText'), initialColor: state.toolOpts.color,
    onChange: color => { state.toolOpts.color = color; },
  });
  const id = new URLSearchParams(location.search).get('project');
  if (!id) { location.replace('index.html'); return; }
  viewport = initViewport($('canvas'));
  initDrawingTools({ sampleColor: viewport.sampleColor });
  bus.on('color:sampled', color => colorPicker.setColor(color));
  initTransformTools();
  initEditTools();
  initTimelinePanel();
  initGraphEditor();
  initGeometryNodes();
  initHistoryPanel();
  initAssetBrowser();
  initAudioPlayback();
  const exportDlg = initExportDialog();
  const props = initPropertiesPanel({
    fit: () => viewport.fit(),
    openExport: exportDlg.open,
    onProjectReplaced: project => {
      const scene = project.scenes[0];
      history.clear();
      setState({
        project, projectId: project.id, sceneId: scene.id,
        layerId: scene.layers[scene.layers.length - 1]?.id ?? null,
        frame: 0, dirty: false, selKey: null,
      });
      viewport.fit();
    },
    onProjectUpdated: () => history.clear(),
  });
  initStudioPanel({
    onCharacterImported: (project, character) => {
      const preferredScene = project.scenes.find(scene =>
        scene.id === state.sceneId && scene.layers.some(layer => layer.character_id === character.id));
      const scene = preferredScene || project.scenes.find(item =>
        item.layers.some(layer => layer.character_id === character.id));
      const layer = scene?.layers.find(item => item.character_id === character.id);
      history.clear();
      setState({
        project,
        sceneId: scene?.id ?? project.scenes[0]?.id,
        layerId: layer?.id ?? null,
        frame: Math.min(state.frame, project.settings.duration_frames - 1),
        dirty: false,
      });
      bus.emit('project:changed');
      viewport.fit();
    },
  });
  const layout = initWorkspaceLayout({ onTool: setTool, onTab: props.showTab });
  initPreferences({ save, resetLayout: layout.resetLayout });
  let project;
  try { project = await Projects.get(id); } catch (e) { toast(e.message, 'err', 6000); return; }
  const scene = project.scenes[0];
  history.clear();
  setState({ project, projectId: id, sceneId: scene.id, layerId: scene.layers[scene.layers.length - 1]?.id ?? null, frame: 0, dirty: false });
  viewport.fit();
  const lastFrame = () => state.project.settings.duration_frames - 1;

  $('undo').onclick = undo; $('redo').onclick = redo; $('save').onclick = save;
  $('fit').onclick = () => viewport.fit();
  $('zoomIn').onclick = () => viewport.zoomBy(1.25);
  $('zoomOut').onclick = () => viewport.zoomBy(0.8);
  document.querySelectorAll('.gp-preset').forEach(btn => {
    btn.onclick = () => {
      state.toolOpts.greasePreset = btn.dataset.gpPreset;
      const presets = { pencil: { color: '#111111', size: 4 }, ink: { color: '#1b2733', size: 2.5 }, charcoal: { color: '#3b3b3b', size: 7 }, highlight: { color: '#f7d154', size: 5 } };
      const next = presets[btn.dataset.gpPreset] || presets.pencil;
      state.toolOpts.color = next.color;
      state.toolOpts.size = next.size;
      syncOpts();
      if (state.tool !== 'grease') setTool('grease');
    };
  });
  $('addLayer').onclick = addLayer;
  $('duplicateLayer').onclick = duplicateLayer;
  $('deleteLayer').onclick = deleteLayer;
  $('gridToggle').onclick = () => {
    const enabled = viewport.toggleGrid();
    $('gridToggle').classList.toggle('on', enabled);
    $('gridToggle').setAttribute('aria-pressed', String(enabled));
  };
  $('onionToggle').onclick = () => {
    const enabled = viewport.toggleOnion();
    $('onionToggle').classList.toggle('on', enabled);
    $('onionToggle').setAttribute('aria-pressed', String(enabled));
  };
  $('projName').onclick = rename;
  $('play').onclick = togglePlay;
  $('firstF').onclick = () => setFrame(0);
  $('prevF').onclick = () => setFrame(state.frame - 1);
  $('nextF').onclick = () => setFrame(state.frame + 1);
  $('lastF').onclick = () => setFrame(lastFrame());
  $('frameNum').onchange = e => { setFrame((+e.target.value || 1) - 1); e.target.blur(); };
  $('endFrame').onchange = e => {
    const n = clamp(Math.round(+e.target.value) || 1, 1, 2000);
    if (n !== state.project.settings.duration_frames) execute(setValue(['settings', 'duration_frames'], n, 'Frame end'));
    if (state.frame > n - 1) setFrame(n - 1);
    e.target.blur(); updateUI();
  };
  $('loop').onclick = () => { setState({ loop: !state.loop }); updateUI(); };
  $('autokey').onclick = () => { setState({ autokey: !state.autokey }); updateUI(); };
  document.querySelectorAll('.tool').forEach(b => { b.onclick = () => setTool(b.dataset.tool); });
  for (const [sid, key, k] of SLIDERS) {
    $(sid).oninput = e => { state.toolOpts[key] = +e.target.value / k; $(sid + 'V').textContent = e.target.value; };
  }
  $('paletteAdd').onclick = addPaletteColor;
  $('shapeFill').onchange = e => { state.toolOpts.shapeFill = e.target.checked; };
  $('fillColor').oninput = e => { state.toolOpts.fillColor = e.target.value; $('fillColorTool').value = e.target.value; };
  $('fillColorTool').oninput = e => { state.toolOpts.fillColor = e.target.value; $('fillColor').value = e.target.value; };
  for (const ch of FIELDS) $('f_' + ch).onchange = e => { setField(ch, parseFloat(e.target.value)); updateFields(); };
  document.querySelectorAll('.key').forEach(b => { b.onclick = () => toggleKey(b.dataset.ch); });
  $('keyAll').onclick = keyAll; $('unkey').onclick = unkeyAll; $('originBtn').onclick = originToCenter;
  $('createMotion').onclick = () => createQuickAnimation('x');
  $('createFade').onclick = () => createQuickAnimation('opacity');
  $('keyEase').onchange = e => setEase(e.target.value);
  $('exportBtn').onclick = exportDlg.open;
  $('eSelAll').onclick = selectAll; $('eDel').onclick = deleteSelected; $('eSmooth').onclick = smoothSelected;

  initShortcuts({
    undo, redo, save, fit: () => viewport.fit(), zoom: f => viewport.zoomBy(f),
    step: d => setFrame(state.frame + d), tool: setTool, size: bumpSize,
    play: togglePlay, key: keyAll, unkey: unkeyAll, jump: jumpKey,
    delKey: () => (state.tool === 'edit' && hasSelection() ? deleteSelected() : deleteSelectedKey()),
    toggleEdit: () => { if (state.tool === 'edit') setTool(prevTool); else { prevTool = state.tool; setTool('edit'); } },
    selectAll: () => { if (state.tool === 'edit') selectAll(); },
    renameLayer, duplicateLayer,
    first: () => setFrame(0), last: () => setFrame(lastFrame()), exp: exportDlg.open,
    toggleCanvasFocus: () => $('canvasFocus').click(),
  });

  bus.on('viewport:down', stopPlay);
  bus.on('project:changed', () => { if (!getLayer()) { const l = getScene().layers; setState({ layerId: l[l.length - 1]?.id ?? null }); } });
  bus.on('project:changed', () => { renderLayers(); renderSwatches(); updateUI(); });
  bus.on('selection', () => { renderLayers(); updateUI(); });
  bus.on('state', updateUI);
  bus.on('history', updateUI);
  bus.on('preview', updateFields);
  bus.on('playback', updateUI);

  // KAE AI writes native editable vector paths directly into the active project.
  window.addEventListener('kae:ai-draw-frames', async event => {
    const task = event.detail || {};
    const finish = (kind, value) => {
      if (kind === 'reject') task.reject?.(value);
      else task.resolve?.(value);
    };
    let overlay = document.getElementById('kaeAIDrawingProgress');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'kaeAIDrawingProgress';
      overlay.style.cssText = 'position:fixed;z-index:2000;left:16px;bottom:16px;max-width:min(560px,calc(100vw - 32px));padding:12px 16px;background:#0b1017;border:1px solid var(--accent,#e8c547);color:var(--text,#eef2f7);font:12px/1.55 ui-monospace,monospace;box-shadow:0 10px 40px #0009;white-space:pre-wrap';
      document.body.append(overlay);
    }
    const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
    try {
      if (!state.project || !Array.isArray(task.frames) || task.frames.length < 4 || task.frames.length > 6) {
        throw new Error('KAE editor is not ready or the AI did not return 4–6 vector frames.');
      }
      const scene = getScene();
      if (!scene) throw new Error('Select a valid scene in the main editor first.');
      const settings = state.project.settings;
      const frames = task.frames;
      const frameSpan = Math.max(2, Math.floor(18 / frames.length));
      const sceneLength = frames.length * frameSpan;
      const occupiedEnds = scene.layers.flatMap(layer =>
        (layer.exposures || [])
          .filter(exposure => state.project.drawings?.[exposure.drawing]?.strokes?.length)
          .map(exposure => (exposure.start || 0) + (exposure.length || 1))
      );
      const startFrame = occupiedEnds.length ? Math.max(...occupiedEnds) : 0;
      const endFrame = startFrame + sceneLength;
      if (endFrame > 2000) throw new Error('This story would exceed KAE’s 2,000-frame project limit.');
      if (settings.duration_frames < endFrame) {
        execute(setValue(['settings', 'duration_frames'], endFrame, 'Extend timeline for AI story'));
      }
      const token = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
      const drawings = [];
      const exposures = [];
      for (let index = 0; index < frames.length; index++) {
        const drawingId = 'ai_d_' + token + '_' + index;
        const drawing = { id: drawingId, name: (task.title || 'AI Story') + ' · Cel ' + (index + 1), strokes: [] };
        execute(setValue(['drawings', drawingId], drawing, 'Create AI drawing cel'));
        drawings.push(drawingId);
        exposures.push({ start: startFrame + index * frameSpan, length: frameSpan, drawing: drawingId });
      }
      const layerId = 'ai_story_' + token;
      const layer = {
        id: layerId, name: (task.title || 'AI Story').slice(0, 90),
        type: 'drawing', visible: true, locked: false, opacity: 1, depth: 1,
        blend: 'normal', exposures, tracks: {},
      };
      const currentSceneIndex = state.project.scenes.findIndex(item => item.id === scene.id);
      execute(insertAt(['scenes', currentSceneIndex, 'layers'], scene.layers.length, layer, 'Add AI story drawing layer'));
      setState({ sceneId: scene.id, layerId, frame: startFrame, dirty: true });
      bus.emit('project:changed', { label: 'AI story drawing started' });
      // Recenter the project before drawing: if the user had panned far away,
      // correct artwork can otherwise be committed off-screen and look like nothing happened.
      viewport.fit();
      viewport.requestRender();
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const canvasElement = $('canvas');
      const captureCanvasPixels = () => {
        const context = canvasElement?.getContext('2d', { willReadFrequently: true });
        return context ? context.getImageData(0, 0, canvasElement.width, canvasElement.height).data : null;
      };
      const pixelsBeforeDrawing = captureCanvasPixels();
      const backgroundHex = /^#[0-9a-f]{6}$/i.test(settings.background || '') ? settings.background : '#ffffff';
      const backgroundRgb = [1, 3, 5].map(index => parseInt(backgroundHex.slice(index, index + 2), 16));
      const makeVisibleColor = color => {
        const hex = typeof color === 'string' && /^#[0-9a-f]{6}(?:[0-9a-f]{2})?$/i.test(color)
          ? color.slice(0, 7) : '#ff6b35';
        const rgb = [1, 3, 5].map(index => parseInt(hex.slice(index, index + 2), 16));
        const distance = Math.hypot(rgb[0] - backgroundRgb[0], rgb[1] - backgroundRgb[1], rgb[2] - backgroundRgb[2]);
        if (distance < 85) {
          const luminance = backgroundRgb[0] * 0.2126 + backgroundRgb[1] * 0.7152 + backgroundRgb[2] * 0.0722;
          return luminance > 128 ? '#e85d25' : '#ffd34e';
        }
        return hex;
      };
      const pixelsDiffer = (before, after) => {
        if (!before || !after || before.length !== after.length) return true;
        for (let index = 0; index < before.length; index += 4) {
          if (before[index] !== after[index] || before[index + 1] !== after[index + 1] ||
              before[index + 2] !== after[index + 2] || before[index + 3] !== after[index + 3]) return true;
        }
        return false;
      };
      overlay.hidden = false;
      overlay.textContent = 'KYRO DRAWING · ' + (task.storyTitle || 'Story') +
        '\nScene ' + (task.sceneNumber || 1) + '/' + (task.totalScenes || 1) + ': ' + (task.title || 'Untitled') +
        '\nFrame 1/4 · preparing canvas…';
      let totalDrawnStrokes = 0;
      for (let frameIndex = 0; frameIndex < frames.length; frameIndex++) {
        const drawingId = drawings[frameIndex];
        const sourceStrokes = Array.isArray(frames[frameIndex]?.strokes) ? frames[frameIndex].strokes : [];
        const usableStrokes = sourceStrokes.filter(source =>
          Array.isArray(source?.commands) && source.commands.length >= 2 &&
          source.commands.every(command => Array.isArray(command) &&
            ['M', 'L', 'Q', 'C', 'Z'].includes(command[0]) &&
            command.slice(1).every(Number.isFinite))
        );
        if (!usableStrokes.length) {
          throw new Error('AI frame ' + (frameIndex + 1) + ' contains no drawable vector paths.');
        }

        const frameNumber = startFrame + frameIndex * frameSpan;
        setFrame(frameNumber);
        setState({ sceneId: scene.id, layerId, frame: frameNumber });
        overlay.textContent = 'KYRO DRAWING · ' + (task.storyTitle || 'Story') +
          '\\nScene ' + (task.sceneNumber || 1) + '/' + (task.totalScenes || 1) + ': ' + (task.title || 'Untitled') +
          '\\nFrame ' + (frameIndex + 1) + '/4 · rendering ' + usableStrokes.length + ' vector paths…';

        // Commit complete paths through KAE's command system. Never mutate a drawing
        // behind the renderer's back: each command clones the data, marks the project
        // dirty, refreshes the viewport, and makes the artwork undoable.
        const completeStrokes = usableStrokes.map((source, strokeIndex) => {
          const color = typeof source.color === 'string' ? source.color : '#ff6b35';
          return {
            ...source,
            id: 'ai_st_' + token + '_' + frameIndex + '_' + strokeIndex,
            tool: 'pen',
            color: makeVisibleColor(color),
            width: Math.max(1.5, Number(source.width) || 3),
            opacity: Number(source.opacity) > 0 ? Math.min(1, Number(source.opacity)) : 1,
            commands: source.commands.map(command => [...command]),
          };
        });
        execute(setValue(
          ['drawings', drawingId, 'strokes'],
          completeStrokes,
          'Render AI frame ' + (frameIndex + 1)
        ));
        // Explicitly repaint after the complete cel is committed. This avoids relying
        // only on debounced UI events while AI is generating several frames.
        setState({ project: state.project, sceneId: scene.id, layerId, frame: frameNumber });
        viewport.requestRender();
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        if (frameIndex === 0) {
          const pixelsAfterDrawing = captureCanvasPixels();
          if (!pixelsDiffer(pixelsBeforeDrawing, pixelsAfterDrawing)) {
            viewport.fit();
            viewport.requestRender();
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            if (!pixelsDiffer(pixelsBeforeDrawing, captureCanvasPixels())) {
              throw new Error('The vector paths were added to the project, but the canvas pixels did not change. KAE stopped instead of falsely reporting a successful drawing.');
            }
          }
        }
        viewport?.requestRender();
        totalDrawnStrokes += completeStrokes.length;
        overlay.textContent = 'KYRO DRAWING · ' + (task.storyTitle || 'Story') +
          '\\nScene ' + (task.sceneNumber || 1) + '/' + (task.totalScenes || 1) + ': ' + (task.title || 'Untitled') +
          '\\nFrame ' + (frameIndex + 1) + '/4 · rendered ' + completeStrokes.length + ' paths (' + totalDrawnStrokes + ' total)';
        await pause(250);
      }
      if (!drawings.some(id => state.project.drawings[id]?.strokes?.length)) {
        throw new Error('KAE received the animation but produced zero visible strokes.');
      }
      setFrame(startFrame);
      await save({ silent: true });
      if (state.dirty) throw new Error('The drawing is on the canvas, but saving failed. Press Save in the editor and check the toast message.');
      overlay.textContent = 'DRAWING SAVED · ' + (task.title || 'Story') +
        '\nNative vector cels are now editable on the main canvas and timeline.';
      finish('resolve', { layerId, startFrame, endFrame });
    } catch (error) {
      if (overlay) overlay.textContent = 'DRAWING PAUSED · ' + error.message + '\nYour current canvas changes remain in the editor.';
      finish('reject', error);
    }
  });

  window.addEventListener('beforeunload', e => { if (state.dirty) { e.preventDefault(); e.returnValue = ''; } });

  syncOpts(); renderSwatches(); renderLayers(); layout.apply(layout.current());
  window.kae = { state, execute, undo, redo }; // debug handle
}

boot();
