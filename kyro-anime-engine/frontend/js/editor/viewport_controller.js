// frontend/js/editor/viewport_controller.js
// Canvas viewport: render loop, wheel/pinch zoom, pan (hand tool / space / middle mouse / two fingers).
// Emits tool hooks for step 4: 'viewport:down' | 'viewport:move' | 'viewport:up' | 'viewport:cancel'
// with world (project) coordinates.
import { bus } from '../core/event_bus.js';
import { state, setState } from '../core/state_manager.js';
import { renderFrame } from '../rendering/renderer.js';
import { getLayer } from '../core/state_manager.js';
import { evaluateTransform } from '../animation/pose_evaluator.js';
import { applyCameraTransform, evaluateCamera } from '../animation/camera_evaluator.js';
import { execute, setValue } from '../core/command_manager.js';
import { drawEditOverlay } from './edit_tools.js';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

export function initViewport(canvas) {
  const ctx = canvas.getContext('2d');
  const workspace = getComputedStyle(document.documentElement).getPropertyValue('--workspace').trim() || '#2b2b33';
  const ptrs = new Map();
  const onionCache = new Map();
  let dpr = 1, queued = false, navLock = false, panning = null, drawing = null, cameraDrag = null, pinch = null, showGrid = true, showOnion = false;

  function resize() {
    const r = canvas.parentElement.getBoundingClientRect();
    dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(r.width * dpr));
    canvas.height = Math.max(1, Math.round(r.height * dpr));
    canvas.style.width = r.width + 'px'; canvas.style.height = r.height + 'px';
    onionCache.clear();
    requestRender();
  }

  function draw() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = workspace; ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (showGrid) drawGrid();
    if (!state.project) return;
    const v = state.view, { width, height } = state.project.settings;
    ctx.setTransform(dpr * v.zoom, 0, 0, dpr * v.zoom, dpr * v.panX, dpr * v.panY);
    ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 20;
    ctx.fillStyle = state.project.settings.background || '#ffffff';
    ctx.fillRect(0, 0, width, height); ctx.restore();
    if (showOnion) drawOnionFrames();
    renderFrame(ctx, state.project, state.sceneId, state.frame, state.preview, {
      transparent: true, showRigOverlay: state.showRigOverlay,
    });
    const scene = state.project.scenes.find(s => s.id === state.sceneId);
    ctx.save();
    const camera = applyCameraTransform(ctx, width, height, scene?.camera, state.frame);
    drawPivot(state.view.zoom * camera.zoom);
    if (state.tool === 'edit') drawEditOverlay(ctx, state.view.zoom * camera.zoom);
    ctx.restore();
  }

  function drawOnionFrames() {
    const layer = getLayer(), exposures = [...(layer?.exposures || [])].sort((a, b) => a.start - b.start);
    if (!exposures.length) return;
    const current = exposures.find(e => state.frame >= e.start && state.frame < e.start + e.length);
    const previous = [...exposures].reverse().find(e => current ? e.start < current.start : e.start + e.length <= state.frame);
    const next = exposures.find(e => current ? e.start > current.start : e.start > state.frame);
    if (previous && previous.drawing !== current?.drawing) drawOnionFrame(previous.start, '#ff7777');
    if (next && next.drawing !== current?.drawing) drawOnionFrame(next.start, '#78aaff');
  }

  function drawOnionFrame(frame, color) {
    let ghost = onionCache.get(frame);
    if (!ghost) {
      ghost = document.createElement('canvas');
      ghost.width = canvas.width;
      ghost.height = canvas.height;
      const ghostCtx = ghost.getContext('2d');
      const view = state.view;
      ghostCtx.setTransform(dpr * view.zoom, 0, 0, dpr * view.zoom, dpr * view.panX, dpr * view.panY);
      renderFrame(ghostCtx, state.project, state.sceneId, frame, null, { transparent: true });
      ghostCtx.setTransform(1, 0, 0, 1, 0, 0);
      ghostCtx.globalCompositeOperation = 'source-in';
      ghostCtx.globalAlpha = 0.38;
      ghostCtx.fillStyle = color;
      ghostCtx.fillRect(0, 0, ghost.width, ghost.height);
      ghostCtx.globalAlpha = 1;
      ghostCtx.globalCompositeOperation = 'source-over';
      onionCache.set(frame, ghost);
    }
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(ghost, 0, 0);
    ctx.restore();
  }

  function drawGrid() {
    const { zoom, panX, panY } = state.view;
    const step = [1, 2, 5, 10, 20, 50, 100, 200, 500].find(value => value * zoom >= 24) || 1000;
    const spacing = step * zoom * dpr;
    const offsetX = ((panX * dpr) % spacing + spacing) % spacing;
    const offsetY = ((panY * dpr) % spacing + spacing) % spacing;
    ctx.beginPath();
    for (let x = offsetX; x < canvas.width; x += spacing) { ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); }
    for (let y = offsetY; y < canvas.height; y += spacing) { ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); }
    ctx.strokeStyle = 'rgba(255,255,255,.055)';
    ctx.lineWidth = Math.max(1, dpr);
    ctx.stroke();
  }

  function drawPivot(effectiveZoom = state.view.zoom) {
    if (!['move', 'rotate', 'scale'].includes(state.tool)) return;
    const l = getLayer(); if (!l || l.visible === false) return;
    const t = evaluateTransform(l, state.frame), r = 9 / effectiveZoom;
    const z = effectiveZoom;
    ctx.save(); ctx.lineWidth = 2 / z; ctx.strokeStyle = '#e87d0d';
    ctx.beginPath(); ctx.arc(t.x, t.y, r, 0, Math.PI * 2);
    ctx.moveTo(t.x - r * 1.6, t.y); ctx.lineTo(t.x + r * 1.6, t.y);
    ctx.moveTo(t.x, t.y - r * 1.6); ctx.lineTo(t.x, t.y + r * 1.6);
    ctx.stroke(); ctx.restore();
  }

  function requestRender() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; draw(); });
  }

  const local = e => { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  const toWorld = e => {
    const p = local(e), v = state.view;
    const scene = state.project?.scenes.find(s => s.id === state.sceneId);
    const camera = evaluateCamera(scene?.camera, state.frame);
    const depth = Math.min(2, Math.max(0, getLayer()?.depth ?? 1));
    const cameraZoomX = 1 + (camera.zoom - 1) * depth;
    const cameraZoomY = 1 + (camera.zoomY - 1) * depth;
    const { width, height } = state.project.settings;
    const radians = -camera.rotation * depth * Math.PI / 180;
    const x = (p.x - v.panX) / v.zoom - width / 2 - camera.x * depth;
    const y = (p.y - v.panY) / v.zoom - height / 2 - camera.y * depth;
    const rotatedX = (x * Math.cos(radians) - y * Math.sin(radians)) / cameraZoomX;
    const rotatedY = (x * Math.sin(radians) + y * Math.cos(radians)) / cameraZoomY;
    return {
      x: width / 2 + rotatedX,
      y: height / 2 + rotatedY,
    };
  };
  const setView = v => setState({ view: v });

  function zoomAt(f, cx, cy) {
    const v = state.view, z = clamp(v.zoom * f, 0.05, 32), k = z / v.zoom;
    setView({ zoom: z, panX: cx - (cx - v.panX) * k, panY: cy - (cy - v.panY) * k });
  }
  const zoomBy = f => zoomAt(f, canvas.clientWidth / 2, canvas.clientHeight / 2);

  function fit() {
    if (!state.project) return;
    const w = canvas.clientWidth, h = canvas.clientHeight, { width, height } = state.project.settings;
    const z = clamp(Math.min((w - 40) / width, (h - 40) / height), 0.05, 32);
    setView({ zoom: z, panX: (w - width * z) / 2, panY: (h - height * z) / 2 });
  }

  function cameraChannel(camera, channel, value) {
    const tracks = { ...(camera.tracks || {}) };
    if (state.autokey || tracks[channel]?.length) {
      const keys = [...(tracks[channel] || [])];
      const key = { t: state.frame, v: value, ease: state.keyEase || 'linear' };
      const index = keys.findIndex(item => item.t === state.frame);
      if (index >= 0) keys[index] = key;
      else keys.push(key);
      keys.sort((a, b) => a.t - b.t);
      tracks[channel] = keys;
    } else {
      camera.transform = { ...(camera.transform || {}), [channel]: value };
    }
    camera.tracks = tracks;
  }

  function setCameraZoomAt(camera, localPoint, nextZoom) {
    const evaluated = evaluateCamera(camera, state.frame);
    const { width, height } = state.project.settings;
    const px = (localPoint.x - state.view.panX) / state.view.zoom;
    const py = (localPoint.y - state.view.panY) / state.view.zoom;
    const radians = evaluated.rotation * Math.PI / 180;
    const dx = px - width / 2 - evaluated.x;
    const dy = py - height / 2 - evaluated.y;
    const worldX = (dx * Math.cos(radians) + dy * Math.sin(radians)) / evaluated.zoom;
    const worldY = (-dx * Math.sin(radians) + dy * Math.cos(radians)) / evaluated.zoomY;
    const newDx = nextZoom * (worldX * Math.cos(radians) - worldY * Math.sin(radians));
    const newDy = nextZoom * (worldX * Math.sin(radians) + worldY * Math.cos(radians));
    cameraChannel(camera, 'x', clamp(px - width / 2 - newDx, -8192, 8192));
    cameraChannel(camera, 'y', clamp(py - height / 2 - newDy, -8192, 8192));
    cameraChannel(camera, 'scale_x', nextZoom);
    cameraChannel(camera, 'scale_y', nextZoom);
  }

  function previewCamera(nextCamera) {
    const sceneIndex = state.project.scenes.findIndex(scene => scene.id === state.sceneId);
    state.project.scenes[sceneIndex].camera = nextCamera;
    bus.emit('project:changed');
  }

  function commitCamera() {
    if (!cameraDrag) return;
    const { sceneIndex, original, preview } = cameraDrag;
    cameraDrag = null;
    if (sceneIndex < 0) return;
    state.project.scenes[sceneIndex].camera = JSON.parse(JSON.stringify(original));
    execute(setValue(['scenes', sceneIndex, 'camera'], preview, 'Move camera'));
  }

  function cancelCamera() {
    if (!cameraDrag) return;
    const { sceneIndex, original } = cameraDrag;
    cameraDrag = null;
    if (sceneIndex < 0) return;
    state.project.scenes[sceneIndex].camera = original;
    bus.emit('project:changed');
  }

  function sampleColor(worldX, worldY) {
    const v = state.view, scene = state.project?.scenes.find(s => s.id === state.sceneId);
    const camera = evaluateCamera(scene?.camera, state.frame);
    const depth = Math.min(2, Math.max(0, getLayer()?.depth ?? 1));
    const cameraZoomX = 1 + (camera.zoom - 1) * depth;
    const cameraZoomY = 1 + (camera.zoomY - 1) * depth;
    const { width, height } = state.project.settings;
    const radians = camera.rotation * depth * Math.PI / 180;
    const dx = worldX - width / 2, dy = worldY - height / 2;
    const sx = width / 2 + camera.x * depth + cameraZoomX * (dx * Math.cos(radians) - dy * Math.sin(radians));
    const sy = height / 2 + camera.y * depth + cameraZoomY * (dx * Math.sin(radians) + dy * Math.cos(radians));
    const x = Math.round((sx * v.zoom + v.panX) * dpr);
    const y = Math.round((sy * v.zoom + v.panY) * dpr);
    if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return null;
    const [r, g, b] = ctx.getImageData(x, y, 1, 1).data;
    return '#' + [r, g, b].map(channel => channel.toString(16).padStart(2, '0')).join('');
  }

  const pinchState = () => {
    const [a, b] = [...ptrs.values()];
    return { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
  };

  canvas.addEventListener('pointerdown', e => {
    canvas.setPointerCapture(e.pointerId);
    ptrs.set(e.pointerId, local(e));
    if (ptrs.size === 2) {
      navLock = true; panning = null;
      if (drawing !== null) { drawing = null; bus.emit('viewport:cancel'); }
      if (cameraDrag) cancelCamera();
      pinch = pinchState(); return;
    }
    if (ptrs.size > 2 || navLock) return;
    if (state.tool === 'pan' || e.button === 1) { panning = e.pointerId; return; }
    if (state.tool === 'camera') {
      const sceneIndex = state.project.scenes.findIndex(scene => scene.id === state.sceneId);
      const camera = state.project.scenes[sceneIndex].camera || { transform: { x: 0, y: 0, scale_x: 1 } };
      cameraDrag = {
        pointerId: e.pointerId,
        sceneIndex,
        origin: local(e),
        original: JSON.parse(JSON.stringify(camera)),
        preview: JSON.parse(JSON.stringify(camera)),
      };
      bus.emit('viewport:down', { ...toWorld(e), pressure: e.pressure, pointerType: e.pointerType });
      return;
    }
    drawing = e.pointerId;
    bus.emit('viewport:down', { ...toWorld(e), pressure: e.pressure, pointerType: e.pointerType });
  });

  canvas.addEventListener('pointermove', e => {
    const prev = ptrs.get(e.pointerId); if (!prev) return;
    const cur = local(e); ptrs.set(e.pointerId, cur);
    if (pinch && ptrs.size === 2) {
      const n = pinchState();
      zoomAt(n.d / pinch.d, n.mx, n.my);
      const v = state.view;
      setView({ ...v, panX: v.panX + (n.mx - pinch.mx), panY: v.panY + (n.my - pinch.my) });
      pinch = n; return;
    }
    if (navLock) return;
    if (panning === e.pointerId) {
      const v = state.view;
      setView({ ...v, panX: v.panX + cur.x - prev.x, panY: v.panY + cur.y - prev.y });
    } else if (cameraDrag?.pointerId === e.pointerId) {
      const base = JSON.parse(JSON.stringify(cameraDrag.original));
      const evaluated = evaluateCamera(base, state.frame);
      const dx = (cur.x - cameraDrag.origin.x) / state.view.zoom;
      const dy = (cur.y - cameraDrag.origin.y) / state.view.zoom;
      const selectedMode = state.cameraMode || 'pan';
      if (selectedMode === 'dolly') {
        setCameraZoomAt(base, cur, clamp(evaluated.zoom * Math.exp(-dy * 0.006), 0.05, 32));
      } else if (selectedMode === 'roll') {
        cameraChannel(base, 'rotation', clamp(evaluated.rotation + dx * 0.5, -3600, 3600));
      } else {
        cameraChannel(base, 'x', clamp(evaluated.x + dx, -8192, 8192));
        cameraChannel(base, 'y', clamp(evaluated.y + dy, -8192, 8192));
      }
      cameraDrag.preview = base;
      previewCamera(base);
    } else if (drawing === e.pointerId) {
      bus.emit('viewport:move', { ...toWorld(e), pressure: e.pressure, pointerType: e.pointerType });
    }
  });

  const end = e => {
    if (!ptrs.delete(e.pointerId)) return;
    if (cameraDrag?.pointerId === e.pointerId) {
      if (e.type === 'pointercancel') cancelCamera();
      else commitCamera();
    }
    if (drawing === e.pointerId) { drawing = null; bus.emit('viewport:up', {}); }
    if (panning === e.pointerId) panning = null;
    if (ptrs.size < 2) pinch = null;
    if (ptrs.size === 0) navLock = false;
  };
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', end);
  canvas.addEventListener('contextmenu', e => e.preventDefault());

  canvas.addEventListener('wheel', e => {
    e.preventDefault();
    const p = local(e);
    const factor = Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0015));
    if (state.tool !== 'camera' || !state.project || state.cameraMode === 'pan') {
      zoomAt(factor, p.x, p.y);
      return;
    }
    const sceneIndex = state.project.scenes.findIndex(scene => scene.id === state.sceneId);
    if (sceneIndex < 0) return;
    const original = state.project.scenes[sceneIndex].camera || { transform: { x: 0, y: 0, scale_x: 1 } };
    const camera = JSON.parse(JSON.stringify(original));
    const evaluated = evaluateCamera(camera, state.frame);
    if (state.cameraMode === 'roll') {
      cameraChannel(camera, 'rotation', clamp(evaluated.rotation - e.deltaY * 0.08, -3600, 3600));
      execute(setValue(['scenes', sceneIndex, 'camera'], camera, 'Roll camera'));
    } else {
      const nextZoom = clamp(evaluated.zoom * factor, 0.05, 32);
      setCameraZoomAt(camera, p, nextZoom);
      execute(setValue(['scenes', sceneIndex, 'camera'], camera, 'Dolly camera'));
    }
  }, { passive: false });

  const cameraModeSelect = document.getElementById('cameraMode');
  if (cameraModeSelect) {
    cameraModeSelect.value = state.cameraMode || 'pan';
    cameraModeSelect.addEventListener('change', () => {
      if (['pan', 'dolly', 'roll'].includes(cameraModeSelect.value)) {
        setState({ cameraMode: cameraModeSelect.value });
      }
    });
  }


  bus.on('state', p => {
    if ('view' in p || 'frame' in p || 'project' in p || 'sceneId' in p || 'layerId' in p) onionCache.clear();
    if ('view' in p || 'frame' in p || 'project' in p || 'sceneId' in p || 'layerId' in p || 'tool' in p) requestRender();
  });
  bus.on('project:changed', () => { onionCache.clear(); requestRender(); });
  bus.on('preview', requestRender);
  new ResizeObserver(resize).observe(canvas.parentElement);
  resize();

  function toggleGrid() {
    showGrid = !showGrid;
    requestRender();
    return showGrid;
  }

  function toggleOnion() {
    showOnion = !showOnion;
    onionCache.clear();
    requestRender();
    return showOnion;
  }

  return { fit, zoomBy, requestRender, toWorld, toggleGrid, toggleOnion, sampleColor };
}
