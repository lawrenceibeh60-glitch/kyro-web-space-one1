// frontend/js/rendering/renderer.js - draws one frame in project coordinates.
// Exposures + animated layer transform/opacity (keyframe tracks).
import { evaluateTransform, evaluateOpacity } from '../animation/pose_evaluator.js';
import { evaluateTrack } from '../animation/interpolation.js';
import { applyCameraDepthTransform, applyCameraTransform } from '../animation/camera_evaluator.js';
import { applyCameraShake } from '../effects/camera_shake.js';
import { drawLightning } from '../effects/lightning.js';
import { drawParticles } from '../effects/particles.js';
import { drawSpeedLines } from '../effects/speed_lines.js';

const BLEND = { normal: 'source-over', multiply: 'multiply', screen: 'screen', overlay: 'overlay', add: 'lighter' };

export function findExposure(layer, frame) {
  const ex = layer.exposures || [];
  for (let i = ex.length - 1; i >= 0; i--) {
    if (frame >= ex[i].start && frame < ex[i].start + ex[i].length) return ex[i];
  }
  return null;
}

export const getLayerTransform = (layer, frame) => evaluateTransform(layer, frame);

const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

function activeEffects(project, sceneId, frame) {
  return (project.effects || []).filter(effect =>
    effect.scene_id === sceneId && effect.enabled !== false
    && frame >= (effect.start_frame ?? 0)
    && frame <= (effect.end_frame ?? project.settings.duration_frames - 1)
  );
}

function effectSeed(id, frame) {
  let value = frame | 0;
  for (let index = 0; index < id.length; index++) value = Math.imul(value ^ id.charCodeAt(index), 16777619);
  return value >>> 0;
}

function seededRandom(seed) {
  let value = seed || 1;
  return () => {
    value = (Math.imul(value, 1664525) + 1013904223) >>> 0;
    return value / 0x100000000;
  };
}

function drawEffects(ctx, effects, width, height, frame) {
  for (const effect of effects) {
    const speed = effect.speed ?? 1;
    const random = seededRandom(effectSeed(
      effect.id,
      effect.type === 'lightning' ? Math.floor(frame * speed / 3) : 0,
    ));
    if (effect.type === 'lightning') {
      drawLightning(ctx, effect, width, height, random);
    } else if (effect.type === 'particles') {
      drawParticles(ctx, effect, width, height, frame, random);
    } else if (effect.type === 'speed_lines') {
      drawSpeedLines(ctx, effect, width, height, frame, random);
    }
  }
}

function drawRigPose(ctx, project, layer, frame) {
  if (!layer.character_id || !layer.character_part_id) return;
  const rig = (project.rigs || []).find(item => item.character_id === layer.character_id);
  const bone = rig?.bones?.find(item => item.character_part_id === layer.character_part_id);
  if (!bone) return;
  const bones = new Map(rig.bones.map(item => [item.id, item]));
  const chain = [];
  const visited = new Set();
  let current = bone;
  while (current && !visited.has(current.id)) {
    visited.add(current.id);
    chain.unshift(current);
    current = current.parent_id ? bones.get(current.parent_id) : null;
  }
  for (const item of chain) {
    const angle = boneRotation(item, frame);
    if (!angle) continue;
    ctx.translate(item.pivot.x, item.pivot.y);
    ctx.rotate(angle * Math.PI / 180);
    ctx.translate(-item.pivot.x, -item.pivot.y);
  }
}

function boneRotation(bone, frame) {
  return bone.tracks?.rotation?.length
    ? evaluateTrack(bone.tracks.rotation, frame)
    : (bone.rotation ?? 0);
}

function rigPivot(bone, bones, frame) {
  const chain = [];
  let parent = bone.parent_id ? bones.get(bone.parent_id) : null;
  const visited = new Set([bone.id]);
  while (parent && !visited.has(parent.id)) {
    visited.add(parent.id);
    chain.unshift(parent);
    parent = parent.parent_id ? bones.get(parent.parent_id) : null;
  }
  let { x, y } = bone.pivot;
  for (const ancestor of chain) {
    const angle = boneRotation(ancestor, frame) * Math.PI / 180;
    const dx = x - ancestor.pivot.x, dy = y - ancestor.pivot.y;
    x = ancestor.pivot.x + dx * Math.cos(angle) - dy * Math.sin(angle);
    y = ancestor.pivot.y + dx * Math.sin(angle) + dy * Math.cos(angle);
  }
  return { x, y };
}

function drawRigOverlay(ctx, project, scene, camera, frame, width, height) {
  const characterIds = new Set((scene?.layers || [])
    .filter(layer => layer.character_id)
    .map(layer => layer.character_id));
  const rigs = (project.rigs || []).filter(rig => characterIds.has(rig.character_id));
  if (!rigs.length) return;
  ctx.save();
  applyCameraTransform(ctx, width, height, camera, frame);
  ctx.strokeStyle = '#52b8ff';
  ctx.fillStyle = '#d9f2ff';
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 3]);
  for (const rig of rigs) {
    const bones = new Map((rig.bones || []).map(bone => [bone.id, bone]));
    for (const bone of bones.values()) {
      const pivot = rigPivot(bone, bones, frame);
      const parent = bone.parent_id ? bones.get(bone.parent_id) : null;
      if (parent) {
        const parentPivot = rigPivot(parent, bones, frame);
        ctx.beginPath();
        ctx.moveTo(parentPivot.x, parentPivot.y);
        ctx.lineTo(pivot.x, pivot.y);
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.arc(pivot.x, pivot.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillText(bone.name, pivot.x + 7, pivot.y - 7);
    }
  }
  ctx.restore();
}

export function drawStroke(ctx, s) {
  const p = s.points;
  const commands = s.commands;
  if ((!Array.isArray(p) || !p.length) && (!Array.isArray(commands) || !commands.length)) return;
  if (s.tool === 'eraser') return;
  const w = s.width ?? 4, color = s.color || '#000', n = p?.length ?? 0, op = s.opacity ?? 1;
  ctx.save();
  ctx.globalAlpha *= op;
  ctx.lineCap = s.line_cap ?? 'round';
  ctx.lineJoin = s.line_join ?? 'round';
  ctx.lineWidth = w; ctx.strokeStyle = color;
  if (commands?.length) {
    ctx.beginPath();
    for (const command of commands) {
      switch (command[0]) {
        case 'M': ctx.moveTo(command[1], command[2]); break;
        case 'L': ctx.lineTo(command[1], command[2]); break;
        case 'Q': ctx.quadraticCurveTo(...command.slice(1)); break;
        case 'C': ctx.bezierCurveTo(...command.slice(1)); break;
        case 'Z': ctx.closePath(); break;
      }
    }
    if (s.fill) { ctx.fillStyle = s.fill; ctx.fill(s.fill_rule ?? 'nonzero'); }
    ctx.stroke();
    ctx.restore();
    return;
  }
  if (n === 1) {
    ctx.fillStyle = color; ctx.beginPath();
    ctx.arc(p[0][0], p[0][1], w * (0.15 + 0.85 * (p[0][2] ?? 1)) / 2, 0, Math.PI * 2); ctx.fill();
    ctx.restore(); return;
  }
  // pressure-sensitive width (pen strokes): per-segment curves
  const varW = op >= 1 && !s.closed && n > 2 && p.some(q => q.length > 2 && q[2] !== p[0][2]);
  if (varW) {
    let prev = p[0];
    for (let i = 1; i < n; i++) {
      const end = i < n - 1 ? mid(p[i], p[i + 1]) : p[i];
      ctx.lineWidth = Math.max(0.5, w * (0.15 + 0.85 * (p[i][2] ?? 1)));
      ctx.beginPath(); ctx.moveTo(prev[0], prev[1]);
      ctx.quadraticCurveTo(p[i][0], p[i][1], end[0], end[1]); ctx.stroke();
      prev = end;
    }
    ctx.restore(); return;
  }
  ctx.beginPath();
  if (s.closed && n >= 3) {
    const m0 = mid(p[n - 1], p[0]);
    ctx.moveTo(m0[0], m0[1]);
    for (let i = 0; i < n; i++) { const m = mid(p[i], p[(i + 1) % n]); ctx.quadraticCurveTo(p[i][0], p[i][1], m[0], m[1]); }
    ctx.closePath();
  } else {
    ctx.moveTo(p[0][0], p[0][1]);
    for (let i = 1; i < n - 1; i++) { const m = mid(p[i], p[i + 1]); ctx.quadraticCurveTo(p[i][0], p[i][1], m[0], m[1]); }
    ctx.lineTo(p[n - 1][0], p[n - 1][1]);
    if (s.closed) ctx.closePath();
  }
  if (s.fill) { ctx.fillStyle = s.fill; ctx.fill(s.fill_rule ?? 'nonzero'); }
  ctx.stroke();
  ctx.restore();
}

// preview (optional): { layerId, drawingId, stroke, hidden:Set<strokeId>, cursor:{x,y,r} }
// opts: { transparent } skips the background fill (PNG / sprite / GIF with alpha)
export function renderFrame(ctx, project, sceneId, frame, preview, opts) {
  const scene = project.scenes.find(s => s.id === sceneId);
  const { width, height, background } = project.settings;
  const effects = activeEffects(project, sceneId, frame);
  const camera = applyCameraShake(scene?.camera, effects, frame);
  ctx.save();
  ctx.beginPath(); ctx.rect(0, 0, width, height); ctx.clip();
  if (!opts?.transparent) { ctx.fillStyle = background || '#ffffff'; ctx.fillRect(0, 0, width, height); }
  for (const layer of scene?.layers || []) {
    if (layer.visible === false) continue;
    const ex = findExposure(layer, frame);
    const strokes = (ex && project.drawings[ex.drawing]?.strokes) || [];
    const pv = preview && preview.layerId === layer.id ? preview : null;
    if (!strokes.length && !pv?.stroke) continue;
    const t = getLayerTransform(layer, frame);
    ctx.save();
    applyCameraDepthTransform(ctx, width, height, camera, frame, layer.depth ?? 1);
    drawRigPose(ctx, project, layer, frame);
    ctx.globalAlpha = evaluateOpacity(layer, frame);
    ctx.globalCompositeOperation = BLEND[layer.blend] || 'source-over';
    ctx.translate(t.x || 0, t.y || 0);
    ctx.rotate((t.rotation || 0) * Math.PI / 180);
    ctx.scale(t.scale_x ?? 1, t.scale_y ?? 1);
    ctx.translate(-(t.anchor_x || 0), -(t.anchor_y || 0));
    const hide = pv && pv.drawingId === ex?.drawing ? pv.hidden : null;
    for (const s of strokes) if (!hide?.has(s.id)) drawStroke(ctx, s);
    if (pv?.stroke) drawStroke(ctx, pv.stroke);
    ctx.restore();
  }
  if (scene?.lights?.length) {
    ctx.save();
    applyCameraTransform(ctx, width, height, camera, frame);
    ctx.globalCompositeOperation = 'screen';
    for (const light of scene.lights) {
      if (!Number.isFinite(light.x) || !Number.isFinite(light.y)
          || !Number.isFinite(light.radius) || !Number.isFinite(light.intensity)
          || light.intensity <= 0) continue;
      const gradient = ctx.createRadialGradient(light.x, light.y, 0, light.x, light.y, light.radius);
      const color = /^#[0-9a-f]{6}$/i.test(light.color || '') ? light.color : '#ffffff';
      const alpha = Math.min(1, Math.max(0, light.intensity));
      gradient.addColorStop(0, `${color}${Math.round(alpha * 255).toString(16).padStart(2, '0')}`);
      gradient.addColorStop(0.35, `${color}${Math.round(alpha * 0.42 * 255).toString(16).padStart(2, '0')}`);
      gradient.addColorStop(1, `${color}00`);
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);
    }
    ctx.restore();
  }
  ctx.save();
  applyCameraTransform(ctx, width, height, camera, frame);
  drawEffects(ctx, effects, width, height, frame);
  ctx.restore();
  if (preview?.cursor) {
    ctx.save();
    const cursorLayer = scene?.layers.find(layer => layer.id === preview.layerId);
    applyCameraDepthTransform(ctx, width, height, camera, frame, cursorLayer?.depth ?? 1);
    const c = preview.cursor;
    ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(0,0,0,.6)'; ctx.beginPath(); ctx.arc(c.x, c.y, c.r, 0, Math.PI * 2); ctx.stroke();
    ctx.lineWidth = 1.5; ctx.strokeStyle = 'rgba(255,255,255,.95)'; ctx.stroke();
    ctx.restore();
  }
  if (opts?.showRigOverlay) {
    drawRigOverlay(ctx, project, scene, camera, frame, width, height);
  }
  ctx.restore();
}
