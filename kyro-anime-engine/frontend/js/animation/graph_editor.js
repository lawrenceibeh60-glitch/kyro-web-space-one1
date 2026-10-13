import { bus } from '../core/event_bus.js';
import { state, getScene } from '../core/state_manager.js';
import { setFrame } from './playback.js';
import { keyFramesOf } from './keyframes.js';
import { evaluateTransform, evaluateOpacity } from './pose_evaluator.js';

const CHANNELS = ['x', 'y', 'rotation', 'scale_x', 'scale_y', 'opacity'];
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

function valueAt(layer, channel, frame) {
  if (!layer) return 0;
  return channel === 'opacity' ? evaluateOpacity(layer, frame) : evaluateTransform(layer, frame)[channel];
}

export function initGraphEditor() {
  const canvas = document.getElementById('graphCanvas');
  const channelSelect = document.getElementById('graphChannel');
  if (!canvas || !channelSelect) return null;

  const ctx = canvas.getContext('2d');
  let currentChannel = channelSelect.value || 'x';
  let keyDrag = null;

  function selectedLayer() {
    const scene = getScene();
    if (!scene) return null;
    return scene.layers.find(l => l.id === state.layerId) || scene.layers[scene.layers.length - 1] || null;
  }

  function totalFrames() {
    return Math.max(1, state.project?.settings?.duration_frames || 1);
  }

  function minMax(layer) {
    if (keyDrag && layer?.id === keyDrag.layerId && currentChannel === keyDrag.channel) {
      return { min: keyDrag.min, max: keyDrag.max };
    }
    const frames = totalFrames();
    const vals = [];
    for (let f = 0; f < frames; f += 1) {
      const v = valueAt(layer, currentChannel, f);
      if (Number.isFinite(v)) vals.push(v);
    }
    if (!vals.length) return { min: 0, max: 1 };
    let min = Math.min(...vals);
    let max = Math.max(...vals);
    if (min === max) { min -= 1; max += 1; }
    return { min, max };
  }

  function draw() {
    if (!state.project) return;
    const layer = selectedLayer();
    const frames = totalFrames();
    const width = canvas.clientWidth || 320;
    const height = canvas.clientHeight || 180;
    const pad = 18;
    const graphW = width - pad * 2;
    const graphH = height - pad * 2;
    const { min, max } = minMax(layer);
    canvas.width = width * (window.devicePixelRatio || 1);
    canvas.height = height * (window.devicePixelRatio || 1);
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = '#4d4d4d';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad, pad);
    ctx.lineTo(pad, height - pad);
    ctx.lineTo(width - pad, height - pad);
    ctx.stroke();

    ctx.fillStyle = '#8a8a8a';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    const yText = [min, (min + max) / 2, max];
    yText.forEach(v => {
      const yy = height - pad - ((v - min) / (max - min || 1)) * graphH;
      ctx.fillText(String(Number(v).toFixed(2)), pad / 2, yy + 3);
    });

    const points = [];
    for (let f = 0; f < frames; f += 1) {
      const x = pad + (f / Math.max(1, frames - 1)) * graphW;
      const value = valueAt(layer, currentChannel, f);
      const y = height - pad - ((value - min) / (max - min || 1)) * graphH;
      points.push({ x, y, f, value });
    }

    if (points.length > 1) {
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i += 1) ctx.lineTo(points[i].x, points[i].y);
      ctx.strokeStyle = '#6bb7ff';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    for (const pt of points) {
      const keyed = keyFramesOf(layer || {}).includes(pt.f) && !!(layer?.tracks?.[currentChannel]?.find(k => k.t === pt.f));
      ctx.fillStyle = keyed ? '#ffb000' : '#d9d9d9';
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, keyed ? 4 : 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    const px = pad + (state.frame / Math.max(1, frames - 1)) * graphW;
    ctx.strokeStyle = '#4a90e2';
    ctx.beginPath();
    ctx.moveTo(px, pad);
    ctx.lineTo(px, height - pad);
    ctx.stroke();
  }

  channelSelect.addEventListener('change', e => {
    currentChannel = CHANNELS.includes(e.target.value) ? e.target.value : currentChannel;
    draw();
  });

  function graphGeometry() {
    const width = canvas.clientWidth || 320;
    const height = canvas.clientHeight || 180;
    const pad = 18;
    const { min, max } = minMax(selectedLayer());
    return { width, height, pad, graphW: width - 2 * pad, graphH: height - 2 * pad, min, max };
  }

  function eventPoint(e) {
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  canvas.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    const layer = selectedLayer();
    const keys = layer?.tracks?.[currentChannel];
    const p = eventPoint(e);
    const g = graphGeometry();
    if (keys?.length) {
      let nearest = null;
      for (let i = 0; i < keys.length; i += 1) {
        const key = keys[i];
        const x = g.pad + (key.t / Math.max(1, totalFrames() - 1)) * g.graphW;
        const y = g.height - g.pad - ((key.v - g.min) / (g.max - g.min || 1)) * g.graphH;
        const distance = Math.hypot(p.x - x, p.y - y);
        if (distance <= 10 && (!nearest || distance < nearest.distance)) nearest = { index: i, distance };
      }
      if (nearest) {
        canvas.setPointerCapture(e.pointerId);
        keyDrag = {
          pointerId: e.pointerId,
          sceneId: state.sceneId,
          layerId: layer.id,
          channel: currentChannel,
          index: nearest.index,
          original: JSON.parse(JSON.stringify(keys)),
          min: g.min,
          max: g.max,
        };
        return;
      }
    }
    const frame = clamp(Math.round((p.x - 18) / Math.max(1, g.width - 36) * (totalFrames() - 1)), 0, totalFrames() - 1);
    setFrame(frame);
    draw();
  });

  canvas.addEventListener('pointermove', e => {
    if (keyDrag?.pointerId !== e.pointerId) return;
    const scene = getScene();
    const layer = scene?.layers.find(item => item.id === keyDrag.layerId);
    if (!layer) return;
    const keys = JSON.parse(JSON.stringify(keyDrag.original));
    const key = keys[keyDrag.index];
    const p = eventPoint(e);
    const g = graphGeometry();
    const previous = keys[keyDrag.index - 1]?.t ?? 0;
    const next = keys[keyDrag.index + 1]?.t ?? totalFrames() - 1;
    const minFrame = previous + (keyDrag.index > 0 ? 1 : 0);
    const maxFrame = next - (keyDrag.index < keys.length - 1 ? 1 : 0);
    key.t = clamp(
      Math.round((p.x - g.pad) / Math.max(1, g.graphW) * (totalFrames() - 1)),
      minFrame,
      maxFrame,
    );
    key.v = keyDrag.min + ((g.height - g.pad - p.y) / Math.max(1, g.graphH)) * (keyDrag.max - keyDrag.min);
    layer.tracks[keyDrag.channel] = keys;
    setFrame(key.t);
    bus.emit('project:changed');
  });

  function finishKeyDrag(e, cancel = false) {
    if (keyDrag?.pointerId !== e.pointerId) return;
    const drag = keyDrag;
    keyDrag = null;
    const sceneIndex = state.project.scenes.findIndex(item => item.id === drag.sceneId);
    const layerIndex = state.project.scenes[sceneIndex]?.layers.findIndex(item => item.id === drag.layerId) ?? -1;
    if (sceneIndex < 0 || layerIndex < 0) return;
    const path = ['scenes', sceneIndex, 'layers', layerIndex, 'tracks', drag.channel];
    const layer = state.project.scenes[sceneIndex].layers[layerIndex];
    const updated = JSON.parse(JSON.stringify(layer.tracks[drag.channel]));
    layer.tracks[drag.channel] = drag.original;
    if (!cancel) {
      updated.sort((a, b) => a.t - b.t);
      execute(setValue(path, updated, `Edit ${drag.channel} key`));
    } else {
      bus.emit('project:changed');
    }
  }

  canvas.addEventListener('pointerup', e => finishKeyDrag(e));
  canvas.addEventListener('pointercancel', e => finishKeyDrag(e, true));

  bus.on('state', p => { if ('frame' in p || 'project' in p || 'sceneId' in p || 'layerId' in p || 'tool' in p) draw(); });
  bus.on('project:changed', draw);
  bus.on('layout', draw);
  bus.on('playback', draw);
  bus.on('selection', draw);

  draw();
  return { draw, setChannel: v => { if (CHANNELS.includes(v)) { currentChannel = v; channelSelect.value = v; draw(); } } };
}
