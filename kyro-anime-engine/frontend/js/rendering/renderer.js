// frontend/js/rendering/renderer.js - draws one frame in project coordinates.
// Exposures + animated layer transform/opacity (keyframe tracks).
import { evaluateTransform, evaluateOpacity } from '../animation/pose_evaluator.js';
import { evaluateTrack } from '../animation/interpolation.js';
import { evaluateRigAnimation } from '../animation/animation_clips.js';
import { deformStrokeForRig } from '../animation/rig_deformer.js';
import { applyCameraDepthTransform, applyCameraTransform } from '../animation/camera_evaluator.js';
import { applyCameraShake } from '../effects/camera_shake.js';
import { drawLightning } from '../effects/lightning.js';
import { drawParticles } from '../effects/particles.js';
import { drawSpeedLines } from '../effects/speed_lines.js';
import { applyCompositorGraph } from './compositing.js';

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

function drawGlowComposite(ctx, effects, width, height) {
  const glow = effects.filter(effect => effect.type === 'glow');
  if (!glow.length) return;
  // Progressive enhancement: skip the glow pass on non-DOM test contexts.
  const documentRef = ctx.canvas?.ownerDocument;
  if (!documentRef?.createElement) return;
  const source = documentRef.createElement('canvas');
  source.width = width;
  source.height = height;
  const sourceCtx = source.getContext('2d');
  if (!sourceCtx) return;
  sourceCtx.drawImage(ctx.canvas, 0, 0, width, height);
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalCompositeOperation = 'screen';
  for (const effect of glow) {
    const intensity = Math.max(0, Math.min(1, Number(effect.intensity ?? 0.5)));
    if (!intensity) continue;
    ctx.globalAlpha = intensity * 0.55;
    ctx.filter = `blur(${Math.round(3 + intensity * 18)}px) saturate(1.2)`;
    ctx.drawImage(source, 0, 0, width, height);
  }
  ctx.filter = 'none';
  ctx.restore();
}

function drawColorGradeComposite(ctx, effects, width, height) {
  const grades = effects.filter(effect => ['color_grade', 'levels'].includes(effect.type));
  if (!grades.length || !ctx.canvas?.ownerDocument?.createElement) return;
  const source = ctx.canvas.ownerDocument.createElement('canvas');
  source.width = width; source.height = height;
  const sourceCtx = source.getContext('2d');
  if (!sourceCtx) return;
  sourceCtx.drawImage(ctx.canvas, 0, 0, width, height);
  let brightness = 1, contrast = 1, saturation = 1;
  for (const effect of grades) {
    const amount = Math.max(0, Math.min(1, Number(effect.intensity ?? 0.5)));
    brightness *= 1 + amount * (effect.type === 'levels' ? 0.24 : 0.12);
    contrast *= 1 + amount * (effect.type === 'levels' ? 0.55 : 0.20);
    saturation *= 1 + amount * (effect.type === 'levels' ? 0.18 : 0.35);
  }
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'copy';
  ctx.filter = `brightness(${brightness * 100}%) contrast(${contrast * 100}%) saturate(${saturation * 100}%)`;
  ctx.drawImage(source, 0, 0, width, height);
  ctx.filter = 'none';
  ctx.restore();
}

function drawVignetteComposite(ctx, effects, width, height) {
  const vignette = effects.filter(effect => effect.type === 'vignette');
  if (!vignette.length || !ctx.createRadialGradient) return;
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  for (const effect of vignette) {
    const strength = Math.max(0, Math.min(1, Number(effect.intensity ?? 0.5)));
    if (!strength) continue;
    const radius = Math.hypot(width, height) * 0.72;
    const gradient = ctx.createRadialGradient(width / 2, height / 2, radius * 0.2, width / 2, height / 2, radius);
    gradient.addColorStop(0, 'rgba(0,0,0,0)');
    gradient.addColorStop(1, `rgba(0,0,0,${strength * 0.78})`);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
  }
  ctx.restore();
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
    } else if (effect.type === 'impact_flash') {
      const elapsed = Math.max(0, frame - (effect.start_frame ?? 0));
      const pulse = 1 - ((elapsed * Math.max(0.1, speed)) % 8) / 8;
      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      ctx.globalAlpha = Math.max(0, Math.min(1, Number(effect.intensity ?? 0.5))) * pulse;
      ctx.fillStyle = /^#[0-9a-f]{6}$/i.test(effect.color || '') ? effect.color : '#ffffff';
      ctx.fillRect(0, 0, width, height);
      ctx.restore();
    }
  }
}

function drawRigPose(ctx, project, layer, frame, pose = null) {
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
    const angle = boneRotation(item, frame, pose);
    if (!angle) continue;
    ctx.translate(item.pivot.x, item.pivot.y);
    ctx.rotate(angle * Math.PI / 180);
    ctx.translate(-item.pivot.x, -item.pivot.y);
  }
}

function boneRotation(bone, frame, pose = null) {
  const base = bone.tracks?.rotation?.length
    ? evaluateTrack(bone.tracks.rotation, frame)
    : (bone.rotation ?? 0);
  return base + (Number.isFinite(pose?.bones?.[bone.id]) ? pose.bones[bone.id] : 0);
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

function transformLayerPoint(point, layer, frame, width, height) {
  const transform = getLayerTransform(layer, frame);
  const anchorX = transform.anchor_x || width / 2;
  const anchorY = transform.anchor_y || height / 2;
  const projected = projectStrokeForYaw(
    { points: [[point.x, point.y]] },
    transform.rotation_y,
    anchorX,
    anchorY,
  ).points[0];
  const sx = (projected[0] - (transform.anchor_x || 0)) * (transform.scale_x ?? 1);
  const sy = (projected[1] - (transform.anchor_y || 0)) * (transform.scale_y ?? 1);
  const radians = (transform.rotation || 0) * Math.PI / 180;
  return {
    x: (transform.x || 0) + sx * Math.cos(radians) - sy * Math.sin(radians),
    y: (transform.y || 0) + sx * Math.sin(radians) + sy * Math.cos(radians),
  };
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
    const characterLayers = (scene?.layers || []).filter(layer => layer.character_id === rig.character_id);
    const pivotFor = bone => {
      const pivot = rigPivot(bone, bones, frame);
      const layer = characterLayers.find(item => item.character_part_id === bone.character_part_id);
      return layer ? transformLayerPoint(pivot, layer, frame, width, height) : pivot;
    };
    for (const bone of bones.values()) {
      const pivot = pivotFor(bone);
      const parent = bone.parent_id ? bones.get(bone.parent_id) : null;
      if (parent) {
        const parentPivot = pivotFor(parent);
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

// Perspective-project a 2D drawing plane as it yaws around the vertical axis.
// This is a genuine perspective 2.5D plane turn; front/profile artwork can crossfade
// over it when a character has alternate pose drawings.
export function projectStrokeForYaw(stroke, yawDegrees, pivotX, pivotY, focalLength = 1400) {
  if (!Number.isFinite(yawDegrees) || Math.abs(yawDegrees) < 0.001) return stroke;
  const radians = Math.max(-180, Math.min(180, yawDegrees)) * Math.PI / 180;
  const cosine = Math.cos(radians), sine = Math.sin(radians);
  const projectPair = pair => {
    const dx = pair[0] - pivotX, dy = pair[1] - pivotY;
    const depth = dx * sine;
    const scale = focalLength / Math.max(focalLength * 0.25, focalLength - depth);
    return [pivotX + dx * cosine * scale, pivotY + dy * scale, ...pair.slice(2)];
  };
  let result = stroke;
  if (Array.isArray(stroke?.points)) {
    result = { ...result, points: stroke.points.map(projectPair) };
  }
  if (Array.isArray(stroke?.commands)) {
    result = {
      ...result,
      commands: stroke.commands.map(command => {
        if (!Array.isArray(command) || command[0] === 'Z') return [...command];
        const next = [...command];
        for (let index = 1; index + 1 < command.length; index += 2) {
          const projected = projectPair([command[index], command[index + 1]]);
          next[index] = projected[0];
          next[index + 1] = projected[1];
        }
        return next;
      }),
    };
  }
  return result;
}

// Screen-space influence overlay for the dedicated weight-paint tool.
export function drawWeightOverlay(ctx, project, sceneId, layerId, frame, boneId, zoom = 1) {
  if (!boneId) return;
  const scene = project.scenes?.find(item => item.id === sceneId);
  const layer = scene?.layers?.find(item => item.id === layerId);
  const exposure = layer && findExposure(layer, frame);
  const drawing = exposure && project.drawings?.[exposure.drawing];
  const rig = layer?.character_id
    ? (project.rigs || []).find(item => item.character_id === layer.character_id)
    : null;
  if (!layer || !drawing || !rig) return;
  const pose = evaluateRigAnimation(rig, frame, { layer, layerTransform: getLayerTransform(layer, frame) });
  const transform = getLayerTransform(layer, frame);
  ctx.save();
  ctx.translate(transform.x || 0, transform.y || 0);
  ctx.rotate((transform.rotation || 0) * Math.PI / 180);
  ctx.scale(transform.scale_x ?? 1, transform.scale_y ?? 1);
  ctx.translate(-(transform.anchor_x || 0), -(transform.anchor_y || 0));
  const radius = Math.max(2, 5 / Math.max(0.1, zoom));
  ctx.lineWidth = 1 / Math.max(0.1, zoom);
  for (const sourceStroke of drawing.strokes || []) {
    const isWeighted = Array.isArray(sourceStroke.skin_weights)
      || Array.isArray(sourceStroke.command_skin_weights);
    const deformedStroke = isWeighted ? deformStrokeForRig(sourceStroke, rig, frame, pose) : sourceStroke;
    const yawPivotX = transform.anchor_x || project.settings.width / 2;
    const yawPivotY = transform.anchor_y || project.settings.height / 2;
    const stroke = projectStrokeForYaw(deformedStroke, transform.rotation_y, yawPivotX, yawPivotY);
    ctx.save();
    if (!isWeighted) drawRigPose(ctx, project, layer, frame, pose);
    const points = [];
    if (Array.isArray(stroke.points)) {
      stroke.points.forEach((point, index) => {
        const influences = stroke.skin_weights?.[index] || [];
        const weight = influences.filter(item => item?.bone_id === boneId)
          .reduce((sum, item) => sum + (Number(item.weight) || 0), 0);
        points.push({ x: point[0], y: point[1], weight });
      });
    } else if (Array.isArray(stroke.commands)) {
      let index = 0;
      for (const command of stroke.commands) {
        if (!Array.isArray(command) || command[0] === 'Z') continue;
        for (let offset = 1; offset + 1 < command.length; offset += 2) {
          const influences = stroke.command_skin_weights?.[index] || [];
          const weight = influences.filter(item => item?.bone_id === boneId)
            .reduce((sum, item) => sum + (Number(item.weight) || 0), 0);
          points.push({ x: command[offset], y: command[offset + 1], weight });
          index++;
        }
      }
    }
    for (const point of points) {
      const w = Math.max(0, Math.min(1, point.weight));
      const red = Math.round(40 + 215 * w);
      const green = Math.round(185 - 125 * w);
      const blue = Math.round(255 - 230 * w);
      ctx.beginPath();
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgb(${red} ${green} ${blue})`;
      ctx.fill();
      ctx.strokeStyle = 'rgba(10, 16, 24, .9)';
      ctx.stroke();
    }
    ctx.restore();
  }
  ctx.restore();
}

export function applyVectorClip(ctx, commands) {
  if (!Array.isArray(commands) || commands.length < 2) return false;
  ctx.beginPath();
  for (const command of commands) {
    if (!Array.isArray(command)) continue;
    switch (command[0]) {
      case 'M': ctx.moveTo(command[1], command[2]); break;
      case 'L': ctx.lineTo(command[1], command[2]); break;
      case 'Q': ctx.quadraticCurveTo(...command.slice(1)); break;
      case 'C': ctx.bezierCurveTo(...command.slice(1)); break;
      case 'Z': ctx.closePath(); break;
    }
  }
  ctx.clip();
  return true;
}

function facialStrokeVisible(stroke, effect, frame) {
  if (!effect) return true;
  const id = String(stroke?.id || '');
  const elapsed = Math.max(0, frame - (effect.start_frame ?? 0));
  const interval = Math.max(8, Number(effect.blink_interval ?? 48));
  const blinkPhase = elapsed % interval;
  const blink = blinkPhase < 2 || blinkPhase === interval - 1;
  if (/^(left|right)-eye-closed$/.test(id)) return blink;
  if (/^(left|right)-(eye-white|iris|pupil|glint)$/.test(id)) return !blink;
  if (id === 'mouth') return false;
  if (id === 'mouth-neutral' || id === 'mouth-smile' || id === 'mouth-open') {
    const keys = Array.isArray(effect.mouth_keys) ? effect.mouth_keys : [];
    const key = [...keys].filter(item => Number.isInteger(item.frame) && item.frame <= frame)
      .sort((a, b) => b.frame - a.frame)[0];
    const shapeName = key?.shape
      ? ({ neutral: 'mouth-neutral', smile: 'mouth-smile', open: 'mouth-open' }[key.shape])
      : null;
    let wanted = shapeName;
    if (!wanted) {
      const cycle = Math.max(4, Number(effect.mouth_cycle ?? 18));
      const phase = (elapsed % cycle) / cycle;
      wanted = phase < 0.28 || phase >= 0.82 ? 'mouth-neutral'
        : phase < 0.55 ? 'mouth-smile' : 'mouth-open';
    }
    return id === wanted;
  }
  return true;
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

function drawMaskLayerTree(ctx, layer, project, frame, camera, width, height, root = true) {
  if (!layer || layer.visible === false) return;
  ctx.save();
  if (root) applyCameraDepthTransform(ctx, width, height, camera, frame, layer.depth ?? 1);
  const transform = getLayerTransform(layer, frame);
  ctx.globalAlpha *= evaluateOpacity(layer, frame);
  ctx.translate(transform.x || 0, transform.y || 0);
  ctx.rotate((transform.rotation || 0) * Math.PI / 180);
  ctx.scale(transform.scale_x ?? 1, transform.scale_y ?? 1);
  ctx.translate(-(transform.anchor_x || 0), -(transform.anchor_y || 0));
  if (layer.clip_path) applyVectorClip(ctx, layer.clip_path);
  if (layer.type === 'group' || layer.type === 'character_instance') {
    for (const child of layer.children || []) {
      drawMaskLayerTree(ctx, child, project, frame, camera, width, height, false);
    }
  } else {
    const exposure = findExposure(layer, frame);
    const strokes = exposure ? (project.drawings?.[exposure.drawing]?.strokes || []) : [];
    for (const stroke of strokes) drawStroke(ctx, stroke);
  }
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
  const documentRef = ctx.canvas?.ownerDocument;
  const layerEffects = effects.filter(effect => ['soft_shadow', 'depth_of_field', 'layer_mask'].includes(effect.type));
  const compositorLayers = [];
  const shadowEffect = layerEffects.find(effect => effect.type === 'soft_shadow');
  const depthEffect = layerEffects.find(effect => effect.type === 'depth_of_field');
  const maskEffects = layerEffects.filter(effect => effect.type === 'layer_mask');
  let layerCanvas = null, layerCtx = null, shadowCanvas = null, shadowCtx = null, maskCanvas = null, maskCtx = null;
  if (documentRef?.createElement) {
    layerCanvas = documentRef.createElement('canvas');
    layerCanvas.width = width; layerCanvas.height = height;
    layerCtx = layerCanvas.getContext('2d');
    if (shadowEffect) {
      shadowCanvas = documentRef.createElement('canvas');
      shadowCanvas.width = width; shadowCanvas.height = height;
      shadowCtx = shadowCanvas.getContext('2d');
    }
    if (maskEffects.length) {
      maskCanvas = documentRef.createElement('canvas');
      maskCanvas.width = width; maskCanvas.height = height;
      maskCtx = maskCanvas.getContext('2d');
    }
    if (!layerCtx) { layerCanvas = null; shadowCtx = null; maskCtx = null; }
  }
  for (const layer of scene?.layers || []) {
    if (layer.visible === false) continue;
    const ex = findExposure(layer, frame);
    const strokes = (ex && project.drawings[ex.drawing]?.strokes) || [];
    const pv = preview && preview.layerId === layer.id ? preview : null;
    if (!strokes.length && !pv?.stroke) continue;
    const targetCtx = layerCtx || ctx;
    if (targetCtx === layerCtx) {
      targetCtx.setTransform(1, 0, 0, 1, 0, 0);
      targetCtx.clearRect(0, 0, width, height);
    }
    const t = getLayerTransform(layer, frame);
    targetCtx.save();
    targetCtx.beginPath(); targetCtx.rect(0, 0, width, height); targetCtx.clip();
    applyCameraDepthTransform(targetCtx, width, height, camera, frame, layer.depth ?? 1);
    const rig = layer.character_id
      ? (project.rigs || []).find(item => item.character_id === layer.character_id)
      : null;
    const rigPose = rig ? evaluateRigAnimation(rig, frame, { layer, layerTransform: t }) : null;
    targetCtx.globalAlpha = evaluateOpacity(layer, frame);
    targetCtx.globalCompositeOperation = targetCtx === layerCtx ? 'source-over' : (BLEND[layer.blend] || 'source-over');
    targetCtx.translate((t.x || 0) + (rigPose?.rootOffset?.x || 0),
      (t.y || 0) + (rigPose?.rootOffset?.y || 0));
    targetCtx.rotate((t.rotation || 0) * Math.PI / 180);
    targetCtx.scale(t.scale_x ?? 1, t.scale_y ?? 1);
    targetCtx.translate(-(t.anchor_x || 0), -(t.anchor_y || 0));
    if (layer.clip_path) applyVectorClip(targetCtx, layer.clip_path);
    const hide = pv && pv.drawingId === ex?.drawing ? pv.hidden : null;
    const facialEffect = effects.find(effect => effect.type === 'facial_animation' && effect.target_layer_id === layer.id);
    const yawPivotX = t.anchor_x || width / 2;
    const yawPivotY = t.anchor_y || height / 2;
    const drawRiggedStroke = sourceStroke => {
      targetCtx.save();
      const isWeighted = rig && (
        Array.isArray(sourceStroke.skin_weights) || Array.isArray(sourceStroke.command_skin_weights)
      );
      let stroke = isWeighted
        ? deformStrokeForRig(sourceStroke, rig, frame, rigPose)
        : sourceStroke;
      stroke = projectStrokeForYaw(stroke, t.rotation_y, yawPivotX, yawPivotY);
      if (!isWeighted) drawRigPose(targetCtx, project, layer, frame, rigPose);
      drawStroke(targetCtx, stroke);
      targetCtx.restore();
    };
    for (const stroke of strokes) {
      if (!hide?.has(stroke.id) && facialStrokeVisible(stroke, facialEffect, frame)) drawRiggedStroke(stroke);
    }
    if (pv?.stroke) drawRiggedStroke(pv.stroke);
    targetCtx.restore();

    if (targetCtx === layerCtx) {
      const maskEffect = maskEffects.find(effect => effect.target_layer_id === layer.id);
      if (maskEffect && maskCtx) {
        const maskLayer = (scene?.layers || []).find(item => item.id === maskEffect.mask_layer_id);
        maskCtx.setTransform(1, 0, 0, 1, 0, 0);
        maskCtx.clearRect(0, 0, width, height);
        if (maskLayer && maskLayer.visible !== false) {
          maskCtx.save();
          maskCtx.beginPath(); maskCtx.rect(0, 0, width, height); maskCtx.clip();
          drawMaskLayerTree(maskCtx, maskLayer, project, frame, camera, width, height, true);
          maskCtx.restore();
        }
        layerCtx.save();
        layerCtx.setTransform(1, 0, 0, 1, 0, 0);
        layerCtx.globalCompositeOperation = 'destination-in';
        layerCtx.drawImage(maskCanvas, 0, 0);
        layerCtx.restore();
      }
      // Keep an isolated, transformed surface per visible layer for layer-aware
      // Alpha Over and Z-depth compositor nodes. The regular render path below
      // remains the default, so projects without advanced nodes render unchanged.
      if (documentRef?.createElement) {
        const layerSnapshot = documentRef.createElement('canvas');
        layerSnapshot.width = width; layerSnapshot.height = height;
        const snapshotCtx = layerSnapshot.getContext('2d');
        if (snapshotCtx) {
          snapshotCtx.drawImage(layerCanvas, 0, 0, width, height);
          compositorLayers.push({
            id: layer.id,
            name: layer.name || layer.id,
            depth: Number(layer.depth ?? 1),
            blend: layer.blend || 'normal',
            canvas: layerSnapshot,
          });
        }
      }
      ctx.save();
      if (shadowEffect && shadowCtx) {
        shadowCtx.setTransform(1, 0, 0, 1, 0, 0);
        shadowCtx.clearRect(0, 0, width, height);
        shadowCtx.drawImage(layerCanvas, 0, 0);
        shadowCtx.globalCompositeOperation = 'source-in';
        shadowCtx.fillStyle = /^#[0-9a-f]{6}$/i.test(shadowEffect.color || '') ? shadowEffect.color : '#171d2a';
        shadowCtx.fillRect(0, 0, width, height);
        shadowCtx.globalCompositeOperation = 'source-over';
        const blur = Math.max(1, Math.min(24, Number(shadowEffect.speed ?? 6)));
        const offset = Math.round(2 + Number(shadowEffect.intensity ?? 0.5) * 5);
        ctx.globalCompositeOperation = 'source-over';
        ctx.globalAlpha = Math.max(0, Math.min(1, Number(shadowEffect.intensity ?? 0.5)));
        ctx.filter = `blur(${blur}px)`;
        ctx.drawImage(shadowCanvas, offset, offset);
        ctx.filter = 'none';
      }
      ctx.globalCompositeOperation = BLEND[layer.blend] || 'source-over';
      ctx.globalAlpha = 1;
      if (depthEffect) {
        const focus = Math.max(0, Math.min(1, Number(depthEffect.focus_depth ?? 0.5)));
        const range = Math.max(0.01, Math.min(1, Number(depthEffect.range ?? 0.25)));
        const difference = Math.min(1, Math.abs((Number(layer.depth ?? 1) - focus) / range));
        const blur = Math.max(0, Math.min(18, difference * Number(depthEffect.intensity ?? 0.5) * 18));
        ctx.filter = blur > 0.25 ? `blur(${blur.toFixed(1)}px)` : 'none';
      }
      ctx.drawImage(layerCanvas, 0, 0);
      ctx.filter = 'none';
      ctx.restore();
    }
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
  drawGlowComposite(ctx, effects, width, height);
  drawColorGradeComposite(ctx, effects, width, height);
  drawVignetteComposite(ctx, effects, width, height);
  if (project.compositor_graph) applyCompositorGraph(ctx, project.compositor_graph, width, height, { layers: compositorLayers, background });
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
