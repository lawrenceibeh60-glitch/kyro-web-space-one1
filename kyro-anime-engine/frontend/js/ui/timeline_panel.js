// frontend/js/ui/timeline_panel.js - dope sheet: ruler, one row per layer (drawing bars + key diamonds), playhead.
// Tap ruler/row = set frame, tap diamond = select key, drag diamond = move keys, X = delete selected.
import { bus } from '../core/event_bus.js';
import { state, getScene } from '../core/state_manager.js';
import { selectLayer } from '../core/selection_manager.js';
import { keyFramesOf } from '../animation/keyframes.js';
import { setFrame, stop, isPlaying } from '../animation/playback.js';
import { moveKeysCmd } from '../editor/transform_tools.js';
import { execute, batch, insertAt, setValue } from '../core/command_manager.js';
import { findExposure } from '../rendering/renderer.js';
import { clamp, frameFromTimelineX, exposureBounds, previewExposureEdit, validateExposureTrack } from '../animation/timeline.js';
import { toast } from './notifications.js';
import { createDrawQueue } from '../rendering/draw_queue.js';

const ROW = 20, RULER = 18, PAD = 6;

export function initTimelinePanel() {
  const $ = id => document.getElementById(id);
  const canvas = $('dope'), content = $('dopeContent'), scroll = $('dopeScroll');
  const names = $('dopeNames'), ctx = canvas.getContext('2d');
  let px = 10, W = 0, H = 0, dpr = 1, canvasDpr = 0;
  let mode = null, drag = null, exposureDrag = null, zoom = 1;
  let selectedMarkerId = null;

  const rows = () => [...(getScene()?.layers || [])].reverse();
  const markers = () => Array.isArray(state.project?.markers) ? state.project.markers : [];
  const selectedMarker = () => markers().find(marker => marker.id === selectedMarkerId) || null;
  const total = () => state.project.settings.duration_frames;
  const frameX = f => PAD + f * px + px / 2;
  const frameAt = x => frameFromTimelineX(x, PAD, px, total());

  const drawQueue = createDrawQueue(() => draw());
  function requestDraw() { drawQueue.request(); }

  function renderNames() {
    names.innerHTML = '';
    const list = rows();
    const scrollTop = scroll.scrollTop;
    const firstRow = clamp(Math.floor((scrollTop - RULER) / ROW), 0, list.length);
    const top = RULER + firstRow * ROW - scrollTop;
    const visibleRows = Math.ceil((names.clientHeight - Math.max(0, top)) / ROW) + 1;
    const spacer = document.createElement('div');
    spacer.className = 'dn-sp';
    spacer.style.height = `${Math.max(0, Math.min(RULER, top))}px`;
    names.append(spacer);
    const rowContainer = document.createElement('div');
    rowContainer.className = 'dn-virtual';
    rowContainer.style.top = `${top}px`;
    for (const l of list.slice(firstRow, firstRow + visibleRows)) {
      const d = document.createElement('div');
      d.className = 'dn' + (l.id === state.layerId ? ' active' : '');
      d.textContent = l.name || l.id;
      const trackColor = /^#[0-9a-f]{6}$/i.test(l.timeline_color || '') ? l.timeline_color : '#e87d0d';
      d.style.borderLeft = `3px solid ${trackColor}`;
      d.style.paddingLeft = '5px';
      d.title = `${l.name || l.id} · ${l.type || 'drawing'} track`;
      d.onclick = () => selectLayer(l.id);
      rowContainer.append(d);
    }
    names.append(rowContainer);
  }

  function diamond(cx, cy, color) {
    ctx.fillStyle = color; ctx.beginPath();
    ctx.moveTo(cx, cy - 5); ctx.lineTo(cx + 5, cy); ctx.lineTo(cx, cy + 5); ctx.lineTo(cx - 5, cy); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = '#111'; ctx.lineWidth = 1; ctx.stroke();
  }

  function draw() {
    if (!state.project) return;
    const n = total(), list = rows();
    px = Math.max(10, (scroll.clientWidth - PAD * 2) / n) * zoom;
    const w = Math.ceil(PAD * 2 + n * px), h = RULER + list.length * ROW;
    dpr = window.devicePixelRatio || 1;
    content.style.width = w + 'px';
    content.style.height = h + 'px';
    const viewWidth = Math.max(1, scroll.clientWidth);
    const viewHeight = Math.max(1, scroll.clientHeight);
    if (viewWidth !== W || viewHeight !== H || dpr !== canvasDpr) {
      W = viewWidth; H = viewHeight;
      canvasDpr = dpr;
      canvas.width = Math.round(viewWidth * dpr);
      canvas.height = Math.round(viewHeight * dpr);
      canvas.style.width = viewWidth + 'px';
      canvas.style.height = viewHeight + 'px';
    }
    const scrollLeft = scroll.scrollLeft, scrollTop = scroll.scrollTop;
    canvas.style.left = scrollLeft + 'px';
    canvas.style.top = scrollTop + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, -scrollLeft * dpr, -scrollTop * dpr);
    ctx.clearRect(scrollLeft, scrollTop, viewWidth, viewHeight);
    ctx.save();
    ctx.beginPath();
    ctx.rect(scrollLeft, scrollTop, viewWidth, viewHeight);
    ctx.clip();

    const firstRow = clamp(Math.floor((scrollTop - RULER) / ROW), 0, list.length);
    const lastRow = clamp(Math.ceil((scrollTop + viewHeight - RULER) / ROW), firstRow, list.length);
    const firstFrame = clamp(Math.floor((scrollLeft - PAD) / px), 0, n);
    const lastFrame = clamp(Math.ceil((scrollLeft + viewWidth - PAD) / px), firstFrame, n);

    for (let i = firstRow; i < lastRow; i++) {
      const l = list[i];
      const y = RULER + i * ROW;
      ctx.fillStyle = i % 2 ? '#262626' : '#2b2b2b';
      ctx.fillRect(scrollLeft, y, viewWidth, ROW);
      if (l.id === state.layerId) {
        ctx.fillStyle = 'rgba(71,114,179,.28)';
        ctx.fillRect(scrollLeft, y, viewWidth, ROW);
      }
      const exposures = l.exposures || [];
      for (let exposureIndex = 0; exposureIndex < exposures.length; exposureIndex++) {
        const e = exposures[exposureIndex];
        if (exposureDrag?.layerId === l.id && exposureDrag.source === e) continue;
        if (e.start >= lastFrame || e.start + e.length <= firstFrame) continue;
        const x = PAD + e.start * px, ew = Math.min(e.length, n - e.start) * px;
        if (ew <= 0) continue;
        const activeExposure = l.id === state.layerId && (selectedExposure === e || findExposure(l, state.frame) === e);
        const trackColor = /^#[0-9a-f]{6}$/i.test(l.timeline_color || '') ? l.timeline_color : '#e87d0d';
        ctx.globalAlpha = activeExposure ? .78 : .48;
        ctx.fillStyle = trackColor;
        ctx.fillRect(x + 1, y + 4, Math.max(1, ew - 2), ROW - 8);
        ctx.globalAlpha = 1;
        ctx.strokeStyle = trackColor; ctx.lineWidth = 1; ctx.strokeRect(x + 1.5, y + 4.5, ew - 3, ROW - 9);
        if (ew > 38) {
          ctx.fillStyle = '#f0d2ad'; ctx.font = '9px sans-serif'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
          ctx.fillText(`D${exposureIndex + 1} · ${e.length}f`, x + 6, y + ROW / 2, ew - 14);
        }
        if (activeExposure && ew >= 12) {
          ctx.fillStyle = '#ffc475';
          ctx.fillRect(x + 1, y + 5, 3, ROW - 10);
          ctx.fillRect(x + ew - 4, y + 5, 3, ROW - 10);
        }
      }
      for (const f of keyFramesOf(l, firstFrame, lastFrame - 1)) {
        if (drag && drag.layerId === l.id && drag.from === f) continue;
        const sel = state.selKey && state.selKey.layerId === l.id && state.selKey.frame === f;
        diamond(frameX(f), y + ROW / 2, sel ? '#ffb000' : '#d9d9d9');
      }
      if (drag && drag.layerId === l.id) diamond(frameX(drag.to), y + ROW / 2, '#ffb000');
      if (exposureDrag?.layerId === l.id) drawExposure(exposureDrag.preview, y, true);
    }

    // ruler
    ctx.fillStyle = '#3d3d3d'; ctx.fillRect(scrollLeft, 0, viewWidth, RULER);
    const steps = [1, 2, 5, 10, 20, 50, 100, 200, 500], step = steps.find(s => s * px >= 34) || 1000;
    ctx.fillStyle = '#8f8f8f'; ctx.font = '10px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (let f = firstFrame; f < lastFrame; f++) {
      const x = frameX(f);
      if (px >= 6) { ctx.fillRect(x, RULER - 4, 1, 4); }
      if (f % step === 0) ctx.fillText(String(f + 1), x, 7);
    }

    // Blender-style named frame markers: colored flags on the ruler and guide lines.
    for (const marker of markers()) {
      const frame = Number(marker.frame);
      if (!Number.isInteger(frame) || frame < firstFrame || frame >= lastFrame || frame >= n) continue;
      const mx = frameX(frame);
      const color = /^#[0-9a-f]{6}$/i.test(marker.color || '') ? marker.color : '#36c5d8';
      ctx.strokeStyle = color;
      ctx.lineWidth = marker.id === selectedMarkerId ? 2 : 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(mx, RULER); ctx.lineTo(mx, h); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = color;
      ctx.beginPath(); ctx.moveTo(mx - 4, 0); ctx.lineTo(mx + 5, 0); ctx.lineTo(mx, 8); ctx.closePath(); ctx.fill();
      if (px >= 8) {
        ctx.font = '9px sans-serif'; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
        ctx.fillText(String(marker.name || 'Marker').slice(0, 18), mx + 5, 8, 110);
      }
    }

    // Preview range boundaries (inclusive), matching Blender's timeline preview range.
    const preview = state.project.preview_range;
    if (preview && Number.isInteger(preview.start) && Number.isInteger(preview.end)
        && preview.start >= 0 && preview.end >= preview.start && preview.end < n) {
      const left = PAD + preview.start * px;
      const right = PAD + (preview.end + 1) * px;
      ctx.fillStyle = 'rgba(54,197,216,.12)';
      ctx.fillRect(Math.max(left, scrollLeft), 0, Math.max(0, Math.min(right, scrollLeft + viewWidth) - Math.max(left, scrollLeft)), RULER);
      ctx.strokeStyle = '#36c5d8';
      ctx.lineWidth = 2;
      for (const x of [frameX(preview.start), frameX(preview.end)]) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }
    }

    // playhead
    const hx = frameX(state.frame);
    ctx.fillStyle = 'rgba(74,144,226,.25)'; ctx.fillRect(PAD + state.frame * px, RULER, px, h - RULER);
    ctx.fillStyle = '#4a90e2'; ctx.fillRect(hx - 1, 0, 2, h);
    ctx.beginPath(); ctx.moveTo(hx - 5, 0); ctx.lineTo(hx + 5, 0); ctx.lineTo(hx, 7); ctx.closePath(); ctx.fill();

    if (isPlaying()) {
      if (hx < scroll.scrollLeft || hx > scroll.scrollLeft + scroll.clientWidth - 20) scroll.scrollLeft = Math.max(0, hx - 40);
    }
    ctx.restore();
  }

  function drawExposure(exposure, y, preview = false) {
    const x = PAD + exposure.start * px, w = Math.max(1, exposure.length * px);
    ctx.fillStyle = preview ? 'rgba(255,180,76,.7)' : 'rgba(232,125,13,.5)';
    ctx.fillRect(x + 1, y + 4, Math.max(1, w - 2), ROW - 8);
    ctx.strokeStyle = '#ffd08b'; ctx.setLineDash([3, 2]); ctx.strokeRect(x + 1.5, y + 4.5, Math.max(1, w - 3), ROW - 9); ctx.setLineDash([]);
  }

  const local = e => {
    const r = canvas.getBoundingClientRect();
    return {
      x: e.clientX - r.left + scroll.scrollLeft,
      y: e.clientY - r.top + scroll.scrollTop,
    };
  };
  let selectedExposure = null;

  function setExposures(layer, exposures, label) {
    const layerIndex = getScene().layers.indexOf(layer);
    if (layerIndex < 0) return;
    const ordered = [...exposures].sort((a, b) => a.start - b.start);
    const validation = validateExposureTrack(ordered, total());
    if (!validation.valid) { toast(validation.reason, 'err'); requestDraw(); return; }
    execute(setValue(['scenes', state.project.scenes.indexOf(getScene()), 'layers', layerIndex, 'exposures'], ordered, label));
  }

  function newDrawing(copyCurrent = false) {
    const layer = getScene()?.layers.find(item => item.id === state.layerId);
    if (!layer || layer.locked || layer.visible === false) {
      toast(!layer ? 'Select a layer first' : layer.locked ? 'Unlock this layer to edit drawings' : 'Show this layer to edit drawings', 'err');
      return;
    }
    const frame = state.frame, sourceExposure = copyCurrent ? findExposure(layer, frame) : null;
    if (copyCurrent && !sourceExposure) { toast('There is no drawing on this frame to duplicate', 'err'); return; }
    let number = 1;
    while (Object.prototype.hasOwnProperty.call(state.project.drawings, `d_${number}`)) number++;
    const id = `d_${number}`;
    const drawing = sourceExposure
      ? JSON.parse(JSON.stringify(state.project.drawings[sourceExposure.drawing]))
      : { id, name: `Drawing ${number}`, strokes: [] };
    drawing.id = id; drawing.name = `Drawing ${number}`;
    const exposures = (layer.exposures || []).flatMap(e => {
      const end = e.start + e.length;
      if (frame < e.start || frame >= end) return [e];
      return [
        ...(e.start < frame ? [{ ...e, length: frame - e.start }] : []),
        ...(frame + 1 < end ? [{ ...e, start: frame + 1, length: end - frame - 1 }] : []),
      ];
    });
    exposures.push({ start: frame, length: 1, drawing: id });
    exposures.sort((a, b) => a.start - b.start);
    const si = state.project.scenes.indexOf(getScene()), li = getScene().layers.indexOf(layer);
    execute(batch([
      setValue(['drawings', id], drawing, copyCurrent ? 'Duplicate drawing' : 'Create drawing'),
      setValue(['scenes', si, 'layers', li, 'exposures'], exposures, copyCurrent ? 'Duplicate exposure' : 'Create exposure'),
    ], copyCurrent ? 'Duplicate exposure' : 'Create exposure'));
    selectedExposure = layer.exposures.find(e => e.start === frame);
    requestDraw();
  }

  function holdDrawing() {
    const layer = getScene()?.layers.find(item => item.id === state.layerId);
    const exposure = layer && findExposure(layer, state.frame);
    if (!layer || !exposure) { toast('Place the playhead on a drawing exposure first', 'err'); return; }
    if (layer.locked) { toast('Unlock this layer to edit drawings', 'err'); return; }
    const next = (layer.exposures || []).filter(e => e.start > exposure.start).reduce((first, e) => Math.min(first, e.start), total());
    const exposures = layer.exposures.map(e => e === exposure ? { ...e, length: Math.max(1, next - e.start) } : e);
    setExposures(layer, exposures, 'Hold drawing');
    selectedExposure = layer.exposures.find(e => e.start === exposure.start);
    requestDraw();
  }

  function clearDrawingExposure() {
    const layer = getScene()?.layers.find(item => item.id === state.layerId);
    const exposure = layer && findExposure(layer, state.frame);
    if (!layer || !exposure) { toast('There is no drawing exposure on this frame', 'err'); return; }
    if (layer.locked) { toast('Unlock this layer to clear its exposure', 'err'); return; }
    setExposures(layer, layer.exposures.filter(item => item !== exposure), 'Clear drawing exposure');
    selectedExposure = null;
    toast(`Cleared drawing exposure at frame ${state.frame + 1}`);
    requestDraw();
  }

  canvas.addEventListener('pointerdown', e => {
    if (!state.project) return;
    stop();
    canvas.setPointerCapture(e.pointerId);
    const p = local(e);
    if (p.y < RULER) { mode = 'scrub'; setFrame(frameAt(p.x)); return; }
    const layer = rows()[Math.floor((p.y - RULER) / ROW)];
    if (!layer) return;
    selectLayer(layer.id);
    const exposures = [...(layer.exposures || [])].sort((a, b) => a.start - b.start);
    const hit = keyFramesOf(layer).find(f => Math.abs(frameX(f) - p.x) <= Math.max(8, px / 2));
    if (hit !== undefined) {
      state.selKey = { layerId: layer.id, frame: hit };
      drag = { layerId: layer.id, from: hit, to: hit }; mode = 'key';
      setFrame(hit); requestDraw(); return;
    }
    const exposureIndex = exposures.findIndex(e => {
      const x = PAD + e.start * px, end = x + e.length * px;
      return p.x >= x && p.x <= end;
    });
    if (exposureIndex >= 0) {
      const exposure = exposures[exposureIndex];
      state.selKey = null;
      setFrame(frameAt(p.x));
      if (layer.locked) { toast('Unlock this layer to edit exposures', 'err'); mode = 'scrub'; return; }
      selectedExposure = exposure;
      const left = PAD + exposure.start * px, right = left + exposure.length * px;
      const edge = Math.abs(p.x - left) <= 6 ? 'left' : Math.abs(p.x - right) <= 6 ? 'right' : 'move';
      const bounds = exposureBounds(exposures, exposureIndex, total());
      exposureDrag = {
        layerId: layer.id, source: exposure, index: exposureIndex, original: { ...exposure }, preview: { ...exposure },
        edge, pointerFrame: frameAt(p.x), bounds,
      };
      mode = 'exposure'; requestDraw(); return;
    }
    state.selKey = null; mode = 'scrub'; setFrame(frameAt(p.x));
    requestDraw();
  });

  // Harmony-style exposure workflow: double-click an empty layer/frame cell to create a new drawing.
  // Single-click remains a non-destructive scrub/select action.
  canvas.addEventListener('dblclick', e => {
    if (!state.project) return;
    const p = local(e);
    if (p.y < RULER) return;
    const rowIndex = Math.floor((p.y - RULER) / ROW);
    const layer = rows()[rowIndex];
    if (!layer) return;
    const frame = frameAt(p.x);
    if (findExposure(layer, frame)) return;
    if (layer.locked || layer.visible === false) {
      toast(layer.locked ? 'Unlock this layer to create a drawing' : 'Show this layer to create a drawing', 'err');
      return;
    }
    selectLayer(layer.id);
    setFrame(frame);
    newDrawing(false);
    toast(`Created drawing at frame ${frame + 1}`);
  });

  canvas.addEventListener('pointermove', e => {
    const p = local(e);
    if (!mode) {
      const row = Math.floor((p.y - RULER) / ROW);
      const layer = rows()[row];
      const exposure = layer?.exposures?.find(item => p.x >= PAD + item.start * px && p.x <= PAD + (item.start + item.length) * px);
      if (exposure) {
        const left = PAD + exposure.start * px, right = left + exposure.length * px;
        canvas.style.cursor = Math.abs(p.x - left) <= 6 || Math.abs(p.x - right) <= 6 ? 'ew-resize' : 'grab';
      } else canvas.style.cursor = p.y < RULER ? 'crosshair' : 'default';
      return;
    }
    if (mode === 'scrub') setFrame(frameAt(p.x));
    else if (drag) drag.to = frameAt(p.x);
    else if (mode === 'exposure' && exposureDrag) {
      const delta = frameAt(p.x) - exposureDrag.pointerFrame;
      exposureDrag.preview = previewExposureEdit(exposureDrag.original, exposureDrag.edge, delta, exposureDrag.bounds);
    }
    const vx = p.x - scroll.scrollLeft;
    if (vx > scroll.clientWidth - 24) scroll.scrollLeft += 8; else if (vx < 24) scroll.scrollLeft -= 8;
    requestDraw();
  });

  const end = () => {
    if (mode === 'key' && drag && drag.to !== drag.from) {
      const d = drag; drag = null;
      moveKeysCmd(d.layerId, d.from, d.to);
      const l = rows().find(x => x.id === d.layerId);
      state.selKey = { layerId: d.layerId, frame: l && keyFramesOf(l).includes(d.to) ? d.to : d.from };
    }
    if (mode === 'exposure' && exposureDrag) {
      const { layerId, source, original, preview } = exposureDrag;
      const layer = getScene()?.layers.find(item => item.id === layerId);
      if (layer && (preview.start !== original.start || preview.length !== original.length)) {
        const exposures = layer.exposures.map(e => e === source ? preview : e).sort((a, b) => a.start - b.start);
        setExposures(layer, exposures, 'Edit exposure');
        selectedExposure = layer.exposures.find(e => e.drawing === preview.drawing && e.start === preview.start);
        setFrame(preview.start);
      }
    }
    exposureDrag = null;
    drag = null; mode = null; requestDraw();
  };
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', () => { exposureDrag = null; drag = null; mode = null; requestDraw(); });

  scroll.addEventListener('scroll', () => {
    renderNames();
    requestDraw();
  });
  function renderMarkers() {
    const list = $('markerList');
    if (!list) return;
    list.innerHTML = '';
    const sorted = [...markers()].sort((a, b) => a.frame - b.frame || a.name.localeCompare(b.name));
    if (!sorted.length) {
      const empty = document.createElement('span');
      empty.className = 'marker-empty';
      empty.textContent = 'No markers yet';
      list.append(empty);
    }
    for (const marker of sorted) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'frame-marker' + (marker.id === selectedMarkerId ? ' selected' : '');
      button.title = `Go to frame ${marker.frame + 1}; right-click to rename`;
      button.textContent = `F${marker.frame + 1} · ${marker.name}`;
      button.style.setProperty('--marker-color', /^#[0-9a-f]{6}$/i.test(marker.color || '') ? marker.color : '#36c5d8');
      button.onclick = () => {
        selectedMarkerId = marker.id;
        setFrame(marker.frame);
        const markerX = frameX(marker.frame);
        if (markerX < scroll.scrollLeft || markerX > scroll.scrollLeft + scroll.clientWidth - 24) {
          scroll.scrollLeft = Math.max(0, markerX - scroll.clientWidth / 2);
        }
        renderMarkers();
        requestDraw();
      };
      button.oncontextmenu = event => {
        event.preventDefault();
        selectedMarkerId = marker.id;
        renameSelectedMarker();
      };
      list.append(button);
    }
    const chosen = !!selectedMarker();
    $('renameMarker').disabled = !chosen;
    $('deleteMarker').disabled = !chosen;
  }

  function addMarker() {
    const name = window.prompt('Marker name (e.g. Impact, Camera Cut, Final Pose):', `Marker ${markers().length + 1}`);
    if (name === null) return;
    const clean = name.trim().slice(0, 120);
    if (!clean) { toast('Enter a marker name', 'err'); return; }
    const frame = clamp(Math.round(state.frame), 0, total() - 1);
    const duplicate = markers().find(m => m.frame === frame && m.name.toLowerCase() === clean.toLowerCase());
    if (duplicate) {
      selectedMarkerId = duplicate.id;
      renderMarkers();
      toast('A marker with that name already exists on this frame');
      return;
    }
    const marker = { id: `marker_${Date.now().toString(36)}`, frame, name: clean, color: '#36c5d8' };
    execute(setValue(['markers'], [...markers(), marker], 'Add frame marker'));
    selectedMarkerId = marker.id;
    renderMarkers();
    requestDraw();
  }

  function renameSelectedMarker() {
    const marker = selectedMarker();
    if (!marker) { toast('Select a marker first', 'err'); return; }
    const name = window.prompt('Rename frame marker:', marker.name);
    if (name === null) return;
    const clean = name.trim().slice(0, 120);
    if (!clean) { toast('Marker name cannot be empty', 'err'); return; }
    const updated = markers().map(item => item.id === marker.id ? { ...item, name: clean } : item);
    execute(setValue(['markers'], updated, 'Rename frame marker'));
    renderMarkers();
    requestDraw();
  }

  function deleteSelectedMarker() {
    const marker = selectedMarker();
    if (!marker) { toast('Select a marker first', 'err'); return; }
    execute(setValue(['markers'], markers().filter(item => item.id !== marker.id), 'Delete frame marker'));
    selectedMarkerId = null;
    renderMarkers();
    requestDraw();
  }

  function syncTimelineFps() {
    const control = $('timelineFps');
    if (control) control.value = String(state.project?.settings?.fps || 24);
  }

  function setTimelineFps() {
    const control = $('timelineFps');
    if (!control || !state.project) return;
    const fps = Number(control.value);
    if (![8, 12, 15, 24, 25, 30, 48, 50, 60].includes(fps)) {
      syncTimelineFps();
      return;
    }
    if (fps === Number(state.project.settings.fps || 24)) return;
    if (isPlaying()) stop();
    execute(setValue(['settings', 'fps'], fps, 'Set project frame rate'));
    syncTimelineFps();
    toast('Project frame rate set to ' + fps + ' FPS');
  }

  function renderPreviewRange() {
    const range = state.project?.preview_range;
    const valid = range && Number.isInteger(range.start) && Number.isInteger(range.end)
      && range.start >= 0 && range.end >= range.start && range.end < total();
    $('previewClear').disabled = !valid || (range.start === 0 && range.end === total() - 1);
    $('previewRangeLabel').textContent = valid
      ? `F${range.start + 1}–F${range.end + 1}`
      : 'Full timeline';
  }

  function setPreviewStart() {
    const frame = clamp(state.frame, 0, total() - 1);
    const old = state.project.preview_range;
    const end = old && Number.isInteger(old.end) ? Math.max(frame, old.end) : total() - 1;
    execute(setValue(['preview_range'], { start: frame, end }, 'Set preview range start'));
    renderPreviewRange();
    requestDraw();
  }

  function setPreviewEnd() {
    const frame = clamp(state.frame, 0, total() - 1);
    const old = state.project.preview_range;
    const start = old && Number.isInteger(old.start) ? Math.min(frame, old.start) : 0;
    execute(setValue(['preview_range'], { start, end: frame }, 'Set preview range end'));
    renderPreviewRange();
    requestDraw();
  }

  function clearPreviewRange() {
    execute(setValue(['preview_range'], { start: 0, end: total() - 1 }, 'Clear preview range'));
    renderPreviewRange();
    requestDraw();
  }

  if ($('timelineFps')) $('timelineFps').addEventListener('change', setTimelineFps);
  $('previewStart').onclick = setPreviewStart;
  $('previewEnd').onclick = setPreviewEnd;
  $('previewClear').onclick = clearPreviewRange;
  $('trackColorButton').onclick = () => {
    const layer = getScene()?.layers.find(item => item.id === state.layerId);
    if (!layer) { toast('Select a track first', 'err'); return; }
    const input = $('trackColorInput');
    input.value = /^#[0-9a-f]{6}$/i.test(layer.timeline_color || '') ? layer.timeline_color : '#e87d0d';
    input.click();
  };
  $('trackColorInput').onchange = () => {
    const scene = getScene(), layer = scene?.layers.find(item => item.id === state.layerId);
    if (!scene || !layer || !/^#[0-9a-f]{6}$/i.test($('trackColorInput').value)) return;
    const si = state.project.scenes.indexOf(scene), li = scene.layers.indexOf(layer);
    execute(setValue(['scenes', si, 'layers', li, 'timeline_color'], $('trackColorInput').value, 'Set timeline track color'));
    renderNames(); requestDraw();
  };
  $('addMarker').onclick = addMarker;
  $('renameMarker').onclick = renameSelectedMarker;
  $('deleteMarker').onclick = deleteSelectedMarker;
  let copiedKeys = null;
  function copyKeyframe() {
    const layer = getScene()?.layers.find(item => item.id === (state.selKey?.layerId || state.layerId));
    const frame = state.selKey?.frame ?? state.frame;
    if (!layer) { toast('Select a track first', 'err'); return; }
    const channels = Object.entries(layer.tracks || {}).map(([name, keys]) => [name, keys.filter(key => key.t === frame).map(key => ({ ...key }))]).filter(([, keys]) => keys.length);
    if (!channels.length) { toast('No transform or opacity keys at this frame', 'err'); return; }
    copiedKeys = { channels, sourceFrame: frame };
    toast('Copied ' + channels.length + ' animated channel(s)');
  }
  function pasteKeyframe() {
    const layer = getScene()?.layers.find(item => item.id === state.layerId);
    if (!layer || !copiedKeys) { toast(!layer ? 'Select a track first' : 'Copy keys before pasting', 'err'); return; }
    const tracks = JSON.parse(JSON.stringify(layer.tracks || {})), frame = state.frame;
    let count = 0;
    for (const [channel, keys] of copiedKeys.channels) {
      tracks[channel] ||= [];
      for (const source of keys) {
        const existing = tracks[channel].find(key => key.t === frame);
        if (existing) { existing.v = source.v; existing.ease = source.ease; }
        else tracks[channel].push({ ...source, t: frame });
        tracks[channel].sort((a, b) => a.t - b.t); count++;
      }
    }
    if (!count) return;
    const scene = getScene(), si = state.project.scenes.indexOf(scene), li = scene.layers.indexOf(layer);
    execute(setValue(['scenes', si, 'layers', li, 'tracks'], tracks, 'Paste keyframes'));
    state.selKey = { layerId: layer.id, frame };
    requestDraw();
  }
  $('copyKeyframe').onclick = copyKeyframe;
  $('pasteKeyframe').onclick = pasteKeyframe;
  $('newDrawing').onclick = () => newDrawing(false);
  $('duplicateDrawing').onclick = () => newDrawing(true);
  $('holdDrawing').onclick = holdDrawing;
  $('clearExposure').onclick = clearDrawingExposure;
  $('dopeZoom').oninput = e => {
    zoom = Number(e.target.value);
    $('dopeZoomValue').textContent = `${zoom}×`;
    requestDraw();
  };
  new ResizeObserver(() => { renderNames(); requestDraw(); }).observe(scroll);

  bus.on('state', p => {
    if ('project' in p) syncTimelineFps();
    if ('frame' in p || 'project' in p || 'sceneId' in p || 'layerId' in p) requestDraw();
    if ('project' in p) {
      if (!markers().some(marker => marker.id === selectedMarkerId)) selectedMarkerId = null;
      renderMarkers();
      renderPreviewRange();
    }
  });
  bus.on('project:changed', () => { selectedExposure = null; syncTimelineFps(); renderNames(); renderMarkers(); renderPreviewRange(); requestDraw(); });
  bus.on('selection', () => { renderNames(); requestDraw(); });
  bus.on('playback', requestDraw);
  renderNames(); renderMarkers(); renderPreviewRange(); requestDraw();
  return { requestDraw, renderNames };
}
