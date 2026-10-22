import { execute, setValue } from '../core/command_manager.js';
import { bus } from '../core/event_bus.js';
import { state, setState } from '../core/state_manager.js';
import { Audio, StudioCharacters } from '../api/studio.js';
import { evaluateTrack } from '../animation/interpolation.js';
import { toLocal } from '../rendering/geometry.js';
import { paintBoneInfluence, nearestBoneInfluence } from '../animation/rig_weights.js';
import { buildAutoRig } from '../animation/auto_rig.js';
import { buildTurnChoreography, countTurnPairs } from '../animation/turn_choreography.js';
import { withRotationLimit } from '../animation/rig_constraints.js';
import { withTwoBoneIK } from '../animation/rig_ik.js';
import { getLayerTransform as evaluateLayerTransform } from '../rendering/renderer.js';
import { pathCoordinateCount } from '../animation/rig_deformer.js';
import { toast } from './notifications.js';

const $ = id => document.getElementById(id);
const clone = value => JSON.parse(JSON.stringify(value));

function option(value, label) {
  const item = document.createElement('option');
  item.value = value;
  item.textContent = label;
  return item;
}

function selectOptions(select, values, selectedValue, emptyLabel) {
  select.replaceChildren();
  if (!values.length) select.append(option('', emptyLabel));
  for (const [value, label] of values) select.append(option(value, label));
  select.value = values.some(([value]) => value === selectedValue) ? selectedValue : (values[0]?.[0] || '');
}

function nextId(prefix, used = []) {
  const ids = new Set(used);
  let suffix = Date.now().toString(36);
  let id = `${prefix}_${suffix}`;
  let index = 1;
  while (ids.has(id)) id = `${prefix}_${suffix}_${index++}`;
  return id;
}

function makeControl(label, min, max, value, onChange, step = 1) {
  const row = document.createElement('label');
  row.className = 'studio-control';
  const title = document.createElement('span');
  title.textContent = label;
  const input = document.createElement('input');
  input.type = 'range'; input.min = min; input.max = max; input.step = step; input.value = value;
  const output = document.createElement('output');
  output.textContent = String(value);
  input.oninput = () => { output.textContent = input.value; };
  input.onchange = () => onChange(Number(input.value));
  row.append(title, input, output);
  return row;
}

export function initStudioPanel({ onCharacterImported }) {
  const root = $('p-studio');
  let activeTab = 'effects';
  let selectedCharacterId = '';

  function showTab(name) {
    activeTab = name;
    root.querySelectorAll('[data-studio-tab]').forEach(button =>
      button.classList.toggle('on', button.dataset.studioTab === name));
    root.querySelectorAll('[data-studio-pane]').forEach(pane =>
      { pane.hidden = pane.dataset.studioPane !== name; });
  }

  function changeProjectArray(key, next, label) {
    execute(setValue([key], next, label));
  }

  function renderEffects() {
    const list = $('effectList');
    list.replaceChildren();
    if (!state.project) return;
    const sceneId = state.sceneId || state.project.scenes[0]?.id;
    const effects = state.project.effects || [];
    const sceneEffects = effects.filter(effect => effect.scene_id === sceneId);
    if (!sceneEffects.length) {
      const empty = document.createElement('div');
      empty.className = 'studio-empty'; empty.textContent = 'No effects in this scene yet.';
      list.append(empty);
    }
    for (const effect of sceneEffects) {
      const row = document.createElement('div'); row.className = 'studio-row';
      const head = document.createElement('div'); head.className = 'studio-row-head';
      const enabled = document.createElement('input'); enabled.type = 'checkbox';
      enabled.checked = effect.enabled !== false;
      enabled.setAttribute('aria-label', `Enable ${effect.type}`);
      enabled.onchange = () => updateEffect(effect.id, { enabled: enabled.checked });
      const name = document.createElement('strong');
      name.textContent = effect.type.replace('_', ' ');
      const remove = document.createElement('button');
      remove.type = 'button'; remove.textContent = '×'; remove.title = 'Remove effect';
      remove.onclick = () => changeProjectArray('effects', effects.filter(item => item.id !== effect.id), 'Remove effect');
      head.append(enabled, name, remove);
      row.append(head);
      row.append(makeControl('Strength', 0, 100, Math.round((effect.intensity ?? 0.5) * 100),
        value => updateEffect(effect.id, { intensity: value / 100 })));
      if (effect.type === 'particles' || effect.type === 'speed_lines') {
        row.append(makeControl('Count', 1, 200, effect.count ?? 36,
          value => updateEffect(effect.id, { count: value })));
      }
      if (!['camera_shake', 'glow'].includes(effect.type)) {
        row.append(makeControl('Speed', 0, 20, effect.speed ?? 1,
          value => updateEffect(effect.id, { speed: value }), 0.1));
      }
      const timing = document.createElement('div'); timing.className = 'xrow n';
      const start = document.createElement('input'); start.type = 'number'; start.min = 1;
      start.value = (effect.start_frame ?? 0) + 1; start.title = 'First active frame';
      start.onchange = () => {
        const startFrame = Math.max(0, Math.round(Number(start.value) || 1) - 1);
        updateEffect(effect.id, {
          start_frame: startFrame,
          end_frame: Math.max(startFrame, effect.end_frame ?? state.project.settings.duration_frames - 1),
        });
      };
      const end = document.createElement('input'); end.type = 'number'; end.min = 1;
      end.value = (effect.end_frame ?? state.project.settings.duration_frames - 1) + 1; end.title = 'Last active frame';
      end.onchange = () => updateEffect(effect.id, {
        end_frame: Math.max(effect.start_frame ?? 0, Math.round(Number(end.value) || 1) - 1),
      });
      timing.append(start, end);
      row.append(timing);
      if (effect.type !== 'camera_shake') {
        const color = document.createElement('input'); color.type = 'color'; color.value = effect.color || '#ffffff';
        color.setAttribute('aria-label', 'Effect color');
        color.onchange = () => updateEffect(effect.id, { color: color.value });
        row.append(color);
      }
      list.append(row);
    }
  }

  function updateEffect(id, patch) {
    const next = (state.project.effects || []).map(effect =>
      effect.id === id ? { ...effect, ...patch } : effect);
    changeProjectArray('effects', next, 'Edit effect');
  }

  function addEffect() {
    const id = nextId('fx', (state.project.effects || []).map(effect => effect.id));
    const type = $('effectType').value;
    const effect = {
      id, scene_id: state.sceneId, type, enabled: true,
      start_frame: 0, end_frame: state.project.settings.duration_frames - 1,
      intensity: 0.5, color: '#ffffff', count: 36, speed: 1,
    };
    changeProjectArray('effects', [...(state.project.effects || []), effect], 'Add effect');
  }

  let weightPaint = null;


  function eachGeometryCoordinate(stroke, callback) {
    if (Array.isArray(stroke.points)) {
      if (!Array.isArray(stroke.skin_weights) || stroke.skin_weights.length !== stroke.points.length) {
        stroke.skin_weights = stroke.points.map(() => []);
      }
      stroke.points.forEach((point, index) => callback(point, stroke.skin_weights, index));
    }
    if (Array.isArray(stroke.commands)) {
      const coords = pathPairs(stroke.commands);
      if (!Array.isArray(stroke.command_skin_weights)
          || stroke.command_skin_weights.length !== pathCoordinateCount(stroke.commands)) {
        stroke.command_skin_weights = coords.map(() => []);
      }
      let index = 0;
      for (const command of stroke.commands) {
        if (!Array.isArray(command) || command[0] === 'Z') continue;
        for (let offset = 1; offset + 1 < command.length; offset += 2) {
          const pair = [command[offset], command[offset + 1]];
          callback(pair, stroke.command_skin_weights, index++);
        }
      }
    }
  }

  function paintAt(point) {
    if (!weightPaint || !state.project) return;
    const localPoint = toLocal(weightPaint.info.layerTransform, point.x, point.y);
    const radius = Number($('weightRadius')?.value || 48);
    const radiusSquared = radius * radius;
    let changed = 0;
    for (const stroke of weightPaint.info.drawing.strokes) {
      eachGeometryCoordinate(stroke, (coordinate, weights, index) => {
        if ((coordinate[0] - localPoint[0]) ** 2 + (coordinate[1] - localPoint[1]) ** 2 > radiusSquared) return;
        weights[index] = paintBoneInfluence(weights[index], weightPaint.boneId, Number($('skinWeight').value));
        changed++;
      });
    }
    if (changed) {
      weightPaint.changed = true;
      weightPaint.touched += changed;
      updateSkinStatus(`Painting ${weightPaint.boneName}: ${weightPaint.touched} point/control-point touches. Release to commit.`);
      bus.emit('preview');
    }
  }

  function startWeightPaint(point) {
    if (state.tool !== 'weight') return;
    const info = activeDrawingInfo();
    const rig = (state.project?.rigs || []).find(item => item.character_id === selectedCharacterId);
    const bone = rig?.bones?.find(item => item.id === $('skinBone')?.value);
    if (!info || !bone) {
      updateSkinStatus('Select a drawing and a bone before painting weights.', true);
      return;
    }
    weightPaint = {
      info: { ...info, layerTransform: (awaitTransform(info.layer, state.frame)) },
      boneId: bone.id,
      boneName: bone.name || bone.id,
      before: clone(info.drawing.strokes),
      changed: false,
      touched: 0,
    };
    paintAt(point);
  }

  function awaitTransform(layer, frame) {
    return evaluateLayerTransform(layer, frame);
  }

  function finishWeightPaint(commit = true) {
    if (!weightPaint) return;
    const active = weightPaint;
    weightPaint = null;
    if (!active.changed) return;
    const after = clone(active.info.drawing.strokes);
    active.info.drawing.strokes = active.before;
    if (commit) {
      execute(setValue(['drawings', active.info.drawingId, 'strokes'], after, 'Paint rig weights'));
      updateSkinStatus(`Committed weights for ${active.touched} point/control-point touches.`);
    } else {
      updateSkinStatus('Weight paint cancelled.');
      bus.emit('preview');
    }
  }

  function activeDrawingInfo() {
    const project = state.project;
    const scene = project?.scenes?.find(item => item.id === state.sceneId) || project?.scenes?.[0];
    const layer = scene?.layers?.find(item => item.id === state.layerId);
    if (!layer) return null;
    let exposure = null;
    for (const item of [...(layer.exposures || [])].reverse()) {
      if (state.frame >= item.start && state.frame < item.start + item.length) { exposure = item; break; }
    }
    const drawing = exposure && project.drawings?.[exposure.drawing];
    return drawing ? { drawing, drawingId: exposure.drawing, layer, scene } : null;
  }

  function pathPairs(commands) {
    const pairs = [];
    for (const command of commands || []) {
      if (!Array.isArray(command) || command[0] === 'Z') continue;
      for (let i = 1; i + 1 < command.length; i += 2) pairs.push([command[i], command[i + 1]]);
    }
    return pairs;
  }


  function updateSkinStatus(message, error = false) {
    const status = $('skinStatus');
    status.textContent = message;
    status.style.color = error ? 'var(--danger, #ff6b6b)' : '';
  }

  function renderSkinTools(rig) {
    const select = $('skinBone');
    if (!select) return;
    const bones = rig?.bones || [];
    selectOptions(select, bones.map(bone => [bone.id, bone.name || bone.id]), select.value, 'Add a bone first');
    if (state.weightBoneId && bones.some(bone => bone.id === state.weightBoneId)) select.value = state.weightBoneId;
    setState({ weightBoneId: select.value || null });
    const info = activeDrawingInfo();
    const usable = !!rig && !!info && bones.length > 0;
    $('skinAutoWeight').disabled = !usable;
    $('skinAssign').disabled = !usable;
    $('skinClear').disabled = !info;
    if (!info) updateSkinStatus('Select a layer with a drawing exposed at the current frame.', true);
    else if (!rig) updateSkinStatus('Create/select a rig for the selected character.');
    else if (!bones.length) updateSkinStatus('Add at least one bone before assigning weights.');
    else {
      const count = info.drawing.strokes.filter(stroke =>
        (Array.isArray(stroke.points) && stroke.points.length)
        || (Array.isArray(stroke.commands) && pathCoordinateCount(stroke.commands) > 0)
      ).length;
      updateSkinStatus(`${info.drawing.name || info.drawingId}: ${count} drawable stroke(s) ready for weighting.`);
    }
  }

  function writeWeightedDrawing(mode) {
    const project = state.project;
    const info = activeDrawingInfo();
    const rig = (project?.rigs || []).find(item => item.character_id === selectedCharacterId);
    const bone = rig?.bones?.find(item => item.id === $('skinBone').value);
    if (!info) { updateSkinStatus('No active drawing. Select an exposed drawing layer.', true); return; }
    if (mode !== 'clear' && !rig?.bones?.length) { updateSkinStatus('The selected rig has no bones.', true); return; }
    const weight = Number($('skinWeight').value);
    const bones = rig?.bones || [];
    const nextStrokes = info.drawing.strokes.map(stroke => {
      if (mode === 'clear') {
        const next = { ...stroke };
        delete next.skin_weights;
        delete next.command_skin_weights;
        return next;
      }
      const next = { ...stroke };
      if (Array.isArray(stroke.points)) {
        next.skin_weights = stroke.points.map(point => mode === 'auto'
          ? nearestBoneInfluence(point, bones)
          : [{ bone_id: bone.id, weight }]);
      }
      if (Array.isArray(stroke.commands)) {
        const coords = pathPairs(stroke.commands);
        next.command_skin_weights = coords.map(point => mode === 'auto'
          ? nearestBoneWeights(point, bones)
          : [{ bone_id: bone.id, weight }]);
      }
      return next;
    });
    const nextDrawing = { ...info.drawing, strokes: nextStrokes };
    execute(setValue(['drawings', info.drawingId], nextDrawing,
      mode === 'auto' ? 'Auto-weight vector drawing' : mode === 'assign' ? 'Assign vector bone weights' : 'Clear vector weights'));
    const vertices = nextStrokes.reduce((total, stroke) =>
      total + (stroke.points?.length || 0) + pathCoordinateCount(stroke.commands), 0);
    updateSkinStatus(mode === 'clear'
      ? `Cleared skin weights from ${nextStrokes.length} stroke(s).`
      : `${mode === 'auto' ? 'Auto-weighted' : 'Assigned bone weights to'} ${vertices} point/control-point coordinates.`);
  }

  function renderWalkControls(rig) {
    const animation = rig?.animation || {};
    $('rigWalkEnabled').checked = animation.type === 'walk' && animation.enabled !== false;
    $('rigWalkCycle').value = animation.cycle_frames ?? 24;
    $('rigWalkSpeed').value = animation.speed ?? 1;
    $('rigWalkStride').value = animation.stride ?? 24;
    $('rigWalkBob').value = animation.bob ?? 5;
    $('rigWalkWeight').value = animation.weight ?? 1;
    $('rigWalkLoop').checked = animation.loop !== false;
    $('rigWalkCycle').disabled = !rig;
    $('rigWalkSpeed').disabled = !rig;
    $('rigWalkStride').disabled = !rig;
    $('rigWalkBob').disabled = !rig;
    $('rigWalkWeight').disabled = !rig;
    $('rigWalkLoop').disabled = !rig;
    $('rigWalkEnabled').disabled = !rig;
    $('rigWalkApply').disabled = !rig;
    $('rigWalkStatus').textContent = !rig
      ? 'Create a rig before applying a procedural clip.'
      : animation.type === 'walk' && animation.enabled !== false
        ? `Walk cycle active · ${animation.cycle_frames ?? 24} frames · ${animation.speed ?? 1}× speed`
        : 'Walk cycle disabled. Enable it to animate this rig.';
  }

  function applyWalkControls() {
    const rig = (state.project?.rigs || []).find(item => item.character_id === selectedCharacterId);
    if (!rig) return;
    const animation = {
      ...(rig.animation || {}),
      type: 'walk',
      enabled: $('rigWalkEnabled').checked,
      cycle_frames: Math.max(4, Math.min(240, Math.round(Number($('rigWalkCycle').value) || 24))),
      speed: Math.max(0.05, Math.min(8, Number($('rigWalkSpeed').value) || 1)),
      stride: Math.max(0, Math.min(100, Number($('rigWalkStride').value) || 0)),
      bob: Math.max(0, Math.min(30, Number($('rigWalkBob').value) || 0)),
      weight: Math.max(0, Math.min(1, Number($('rigWalkWeight').value) || 0)),
      loop: $('rigWalkLoop').checked,
    };
    updateRig({ ...clone(rig), animation });
    $('rigWalkStrideValue').textContent = String(animation.stride);
    $('rigWalkBobValue').textContent = String(animation.bob);
    $('rigWalkWeightValue').textContent = animation.weight.toFixed(2);
    $('rigWalkStatus').textContent = animation.enabled
      ? `Walk cycle active · ${animation.cycle_frames} frames · ${animation.speed}× speed`
      : 'Walk cycle disabled.';
  }

  function renderTurnControls() {
    const scene = state.project?.scenes?.find(item => item.id === state.sceneId) || state.project?.scenes?.[0];
    const pairs = scene ? countTurnPairs(scene.layers, selectedCharacterId) : 0;
    $('rigTurnApply').disabled = pairs === 0;
    if (document.activeElement !== $('turnStartFrame')) $('turnStartFrame').value = state.frame ?? 0;
    $('rigTurnStatus').textContent = pairs
      ? `${pairs} matching front/profile part pair(s) found.`
      : 'This character has no matching front/profile layer pairs. Add alternate pose drawings first.';
  }

  function applyTurnChoreography() {
    const project = state.project;
    const sceneIndex = (project.scenes || []).findIndex(item => item.id === state.sceneId);
    const scene = project.scenes?.[sceneIndex];
    if (!scene) return;
    try {
      const result = buildTurnChoreography(
        scene.layers,
        selectedCharacterId,
        Number($('turnStartFrame').value),
        Number($('turnDuration').value),
        project.settings.duration_frames - 1,
      );
      execute(setValue(['scenes', sceneIndex, 'layers'], result.layers, 'Build front/profile turn'));
      $('rigTurnStatus').textContent =
        `Turn applied to ${result.pairCount} part pair(s), frames ${result.startFrame}–${result.endFrame}.`;
      toast('Front/profile turn keyframes created.', 'ok');
    } catch (error) {
      $('rigTurnStatus').textContent = error.message || 'Could not build the turn.';
      toast(error.message || 'Could not build the turn.', 'err');
    }
  }

  function renderRotationLimitControls(rig) {
    const select = $('constraintBone');
    const bones = rig?.bones || [];
    selectOptions(select, bones.map(bone => [bone.id, bone.name || bone.id]), select.value, 'Add a bone first');
    const bone = bones.find(item => item.id === select.value);
    const constraint = (rig?.constraints || []).find(item => item.type === 'rotation_limit' && item.bone_id === bone?.id);
    $('rotationLimitEnabled').checked = !!constraint;
    $('rotationLimitMin').value = constraint?.min ?? -90;
    $('rotationLimitMax').value = constraint?.max ?? 90;
    const enabled = !!rig && !!bone;
    select.disabled = !enabled;
    $('rotationLimitEnabled').disabled = !enabled;
    $('rotationLimitMin').disabled = !enabled || !constraint && !$('rotationLimitEnabled').checked;
    $('rotationLimitMax').disabled = !enabled || !constraint && !$('rotationLimitEnabled').checked;
    $('rotationLimitApply').disabled = !enabled;
    $('rotationLimitStatus').textContent = !bone
      ? 'Create a rig and add a bone to configure joint limits.'
      : constraint
        ? `Rotation limited to ${constraint.min}° … ${constraint.max}°.`
        : 'No rotation limit is active for this bone.';
  }

  function applyRotationLimit() {
    const rig = (state.project?.rigs || []).find(item => item.character_id === selectedCharacterId);
    const boneId = $('constraintBone').value;
    if (!rig || !boneId) return;
    const enabled = $('rotationLimitEnabled').checked;
    try {
      const constraints = withRotationLimit(
        rig.constraints || [], boneId, enabled,
        Number($('rotationLimitMin').value), Number($('rotationLimitMax').value), 1,
      );
      updateRig({ ...clone(rig), constraints });
      $('rotationLimitStatus').textContent = enabled
        ? `Rotation limit applied: ${Number($('rotationLimitMin').value)}° … ${Number($('rotationLimitMax').value)}°.`
        : 'Rotation limit removed.';
      toast(enabled ? 'Joint rotation limit applied.' : 'Joint rotation limit removed.', 'ok');
    } catch (error) {
      $('rotationLimitStatus').textContent = error.message || 'Invalid rotation limit.';
      toast(error.message || 'Invalid rotation limit.', 'err');
    }
  }

  function selectedIKId() {
    const upper = $('ikUpperBone')?.value || '';
    const lower = $('ikLowerBone')?.value || '';
    return `ik_${upper}_${lower}`;
  }

  function renderIKControls(rig) {
    const bones = rig?.bones || [];
    const options = bones.map(bone => [bone.id, bone.name || bone.id]);
    selectOptions($('ikUpperBone'), options, $('ikUpperBone').value, 'Select upper bone');
    selectOptions($('ikLowerBone'), options, $('ikLowerBone').value, 'Select lower bone');
    const constraint = (rig?.constraints || []).find(item =>
      item.type === 'ik_two_bone'
      && item.upper_bone_id === $('ikUpperBone').value
      && item.lower_bone_id === $('ikLowerBone').value);
    if (constraint) {
      $('ikTargetX').value = constraint.target.x;
      $('ikTargetY').value = constraint.target.y;
      $('ikBend').value = String(constraint.bend || 1);
    }
    const enabled = !!rig && bones.length >= 2;
    for (const id of ['ikUpperBone', 'ikLowerBone', 'ikTargetX', 'ikTargetY', 'ikBend', 'ikApply', 'ikRemove']) {
      $(id).disabled = !enabled;
    }
    $('ikStatus').textContent = constraint
      ? `Saved target (${constraint.target.x}, ${constraint.target.y}) for this bone pair.`
      : 'Choose two bones, set the end target, then save.';
  }

  function applyIKTarget() {
    const rig = (state.project?.rigs || []).find(item => item.character_id === selectedCharacterId);
    if (!rig) return;
    const upperBoneId = $('ikUpperBone').value;
    const lowerBoneId = $('ikLowerBone').value;
    const upper = rig.bones.find(bone => bone.id === upperBoneId);
    const lower = rig.bones.find(bone => bone.id === lowerBoneId);
    if (!upper || !lower || upper.id === lower.id) {
      $('ikStatus').textContent = 'Choose two distinct bones.';
      return;
    }
    const id = selectedIKId();
    try {
      const constraints = withTwoBoneIK(rig.constraints || [], {
        id, upperBoneId, lowerBoneId,
        targetX: Number($('ikTargetX').value),
        targetY: Number($('ikTargetY').value),
        bend: Number($('ikBend').value),
      });
      updateRig({ ...clone(rig), constraints });
      $('ikStatus').textContent = 'IK target saved. It will be applied during procedural rig playback.';
      toast('IK target saved.', 'ok');
    } catch (error) {
      $('ikStatus').textContent = error.message || 'Invalid IK target.';
      toast(error.message || 'Invalid IK target.', 'err');
    }
  }

  function removeIKTarget() {
    const rig = (state.project?.rigs || []).find(item => item.character_id === selectedCharacterId);
    if (!rig) return;
    const upperBoneId = $('ikUpperBone').value;
    const lowerBoneId = $('ikLowerBone').value;
    const constraints = (rig.constraints || []).filter(item => !(
      item.type === 'ik_two_bone'
      && item.upper_bone_id === upperBoneId
      && item.lower_bone_id === lowerBoneId
    ));
    updateRig({ ...clone(rig), constraints });
    $('ikStatus').textContent = 'IK target removed.';
    toast('IK target removed.', 'ok');
  }

  function renderRig() {
    if (!state.project) return;
    const characters = state.project.characters || [];
    const characterOptions = characters.map(character => [character.id, `${character.name || character.id} · ${character.id}`]);
    if (!characters.some(character => character.id === selectedCharacterId)) {
      selectedCharacterId = characterOptions[0]?.[0] || '';
    }
    // The viewport uses this selection to draw and drag the active rig's IK handles.
    state.activeRigCharacterId = selectedCharacterId;
    selectOptions($('rigCharacter'), characterOptions, selectedCharacterId, 'Import or generate a character first');
    const character = characters.find(item => item.id === selectedCharacterId);
    const rigs = state.project.rigs || [];
    const rig = rigs.find(item => item.character_id === selectedCharacterId);
    $('rigEditor').hidden = !rig;
    $('rigCreate').disabled = !character;
    $('rigCreate').textContent = rig ? `Rig active: ${rig.name}` : 'Create / select rig';
    const attachedParts = new Set((rig?.bones || []).map(bone => bone.character_part_id));
    const partOptions = (character?.parts || [])
      .filter(part => !attachedParts.has(part.id))
      .map(part => [part.id, part.name || part.id]);
    selectOptions($('bonePart'), partOptions, $('bonePart').value, 'No character parts');
    const boneOptions = (rig?.bones || []).map(bone => [bone.id, bone.name || bone.id]);
    selectOptions($('boneParent'), [['', 'No parent'], ...boneOptions], $('boneParent').value, 'No bones');
    renderRotationLimitControls(rig);
    renderIKControls(rig);
    renderSkinTools(rig);
    renderWalkControls(rig);
    renderTurnControls();
    const list = $('boneList');
    list.replaceChildren();
    for (const bone of rig?.bones || []) {
      const row = document.createElement('div'); row.className = 'studio-row studio-bone';
      const name = document.createElement('strong'); name.textContent = `${bone.name} → ${bone.character_part_id}`;
      const rotation = document.createElement('input');
      rotation.type = 'range'; rotation.min = -180; rotation.max = 180;
      rotation.value = bone.tracks?.rotation?.length
        ? evaluateTrack(bone.tracks.rotation, state.frame)
        : (bone.rotation ?? 0);
      rotation.title = 'Bone rotation';
      rotation.onchange = () => {
        if (bone.tracks?.rotation?.length) {
          const tracks = clone(bone.tracks);
          const keys = [...tracks.rotation];
          const keyframe = { t: state.frame, v: Number(rotation.value), ease: state.keyEase || 'linear' };
          const index = keys.findIndex(item => item.t === state.frame);
          if (index >= 0) keys[index] = keyframe; else keys.push(keyframe);
          keys.sort((a, b) => a.t - b.t);
          tracks.rotation = keys;
          updateBone(rig, bone.id, { tracks });
        } else {
          updateBone(rig, bone.id, { rotation: Number(rotation.value) });
        }
      };
      const key = document.createElement('button'); key.type = 'button'; key.textContent = 'Key';
      key.title = `Key rotation at frame ${state.frame + 1}`;
      key.onclick = () => {
        const tracks = clone(bone.tracks || {});
        const keys = [...(tracks.rotation || [])];
        const keyframe = { t: state.frame, v: Number(rotation.value), ease: state.keyEase || 'linear' };
        const index = keys.findIndex(item => item.t === state.frame);
        if (index >= 0) keys[index] = keyframe; else keys.push(keyframe);
        keys.sort((a, b) => a.t - b.t);
        tracks.rotation = keys;
        updateBone(rig, bone.id, { tracks });
      };
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×';
      remove.title = 'Remove bone';
      remove.onclick = () => {
        const nextRig = clone(rig);
        const parentId = nextRig.bones.find(item => item.id === bone.id)?.parent_id || null;
        nextRig.bones = nextRig.bones.filter(item => item.id !== bone.id);
        nextRig.bones.forEach(item => { if (item.parent_id === bone.id) item.parent_id = parentId; });
        nextRig.constraints = (nextRig.constraints || []).filter(item => item.bone_id !== bone.id && item.target_bone_id !== bone.id);
        updateRig(nextRig);
      };
      row.append(name, rotation, key, remove);
      list.append(row);
    }
    if (rig && !rig.bones.length) {
      const empty = document.createElement('div'); empty.className = 'studio-empty';
      empty.textContent = 'Add bones and assign them to character parts to rig the drawing.';
      list.append(empty);
    }
  }

  function updateRig(rig) {
    const rigs = state.project.rigs || [];
    const next = rigs.some(item => item.id === rig.id)
      ? rigs.map(item => item.id === rig.id ? rig : item)
      : [...rigs, rig];
    changeProjectArray('rigs', next, 'Edit character rig');
  }

  function updateBone(rig, boneId, patch) {
    const nextRig = clone(rig);
    nextRig.bones = nextRig.bones.map(bone =>
      bone.id === boneId ? { ...bone, ...patch } : bone);
    updateRig(nextRig);
  }

  function createRig() {
    const character = (state.project.characters || []).find(item => item.id === selectedCharacterId);
    if (!character) return;
    if ((state.project.rigs || []).some(item => item.character_id === character.id)) return;
    const rig = {
      id: nextId('rig', (state.project.rigs || []).map(item => item.id)),
      name: `${character.name || character.id} Rig`,
      character_id: character.id,
      bones: [],
    };
    changeProjectArray('rigs', [...(state.project.rigs || []), rig], 'Create character rig');
  }

  function autoRig() {
    const character = (state.project.characters || []).find(item => item.id === selectedCharacterId);
    const rig = (state.project.rigs || []).find(item => item.character_id === selectedCharacterId);
    if (!character || !rig) {
      toast('Create/select a character rig before auto-rigging.', 'err');
      return;
    }
    try {
      const result = buildAutoRig(character, rig, state.project.settings);
      if (!result.addedCount) {
        toast('Every character part already has a bone.', 'ok');
        return;
      }
      updateRig(result.rig);
      toast(`Auto-rigged ${result.addedCount} part(s); ${result.totalCount} bones total.`, 'ok', 5000);
    } catch (error) {
      toast(error.message || 'Could not auto-rig this character.', 'err');
    }
  }

  function deleteRig() {
    const rigs = state.project.rigs || [];
    const rig = rigs.find(item => item.character_id === selectedCharacterId);
    if (!rig) return;
    changeProjectArray('rigs', rigs.filter(item => item.id !== rig.id), 'Remove character rig');
  }

  function addBone() {
    const rig = (state.project.rigs || []).find(item => item.character_id === selectedCharacterId);
    if (!rig || !$('bonePart').value) return;
    const name = $('boneName').value.trim() || 'Bone';
    const id = nextId('bone', rig.bones.map(item => item.id));
    updateRig({
      ...clone(rig),
      bones: [...rig.bones, {
        id, name, parent_id: $('boneParent').value || null,
        character_part_id: $('bonePart').value,
        pivot: {
          x: Number($('boneX').value || state.project.settings.width / 2),
          y: Number($('boneY').value || state.project.settings.height * 0.44),
        },
        rotation: 0,
      }],
    });
  }

  async function generateCharacter() {
    const id = $('generatorId').value.trim();
    const name = $('generatorName').value.trim();
    if (!id || !name) {
      toast('Enter a stable character ID and name before generating.', 'err');
      return;
    }
    const button = $('generateCharacter');
    button.disabled = true;
    try {
      const result = await StudioCharacters.generate(state.projectId, {
        id, name,
        hairstyle: $('generatorHair').value,
        expression: $('generatorExpression').value,
        hair_color: $('generatorHairColor').value,
        eye_color: $('generatorEyeColor').value,
        skin_color: $('generatorSkinColor').value,
        outfit_color: $('generatorOutfitColor').value,
      });
      onCharacterImported?.(result.project, result.character);
      selectedCharacterId = result.character.id;
      renderRig();
      toast(`Generated ${result.character.name} · ${result.character.parts.length} editable parts`, 'ok', 5000);
    } catch (error) {
      const details = error.details?.length ? `: ${error.details.slice(0, 4).join('; ')}` : '';
      toast(`${error.message}${details}`, 'err', 6000);
    } finally {
      button.disabled = false;
    }
  }

  function renderCharacterList() {
    const list = $('generatorCharacters');
    list.replaceChildren();
    for (const character of state.project?.characters || []) {
      const row = document.createElement('div'); row.className = 'studio-row-head';
      const name = document.createElement('strong'); name.textContent = `${character.name || character.id} · ${character.id}`;
      const use = document.createElement('button'); use.type = 'button'; use.textContent = 'Edit';
      use.onclick = () => {
        $('generatorId').value = character.id;
        $('generatorName').value = character.name || character.id;
      };
      row.append(name, use); list.append(row);
    }
  }

  function renderAudio() {
    if (!state.project) return;
    if (!$('audioStart').value) $('audioStart').value = state.frame + 1;
    const list = $('audioList'); list.replaceChildren();
    for (const clip of state.project.audio || []) {
      const row = document.createElement('div'); row.className = 'studio-row';
      const head = document.createElement('div'); head.className = 'studio-row-head';
      const name = document.createElement('strong'); name.textContent = `${clip.name} · F${clip.start_frame + 1}`;
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×';
      remove.title = 'Remove audio clip';
      remove.onclick = () =>
        changeProjectArray('audio', (state.project.audio || []).filter(item => item.id !== clip.id), 'Remove audio clip');
      head.append(name, remove);
      row.append(head);
      const startRow = document.createElement('div'); startRow.className = 'xrow n';
      const startLabel = document.createElement('span'); startLabel.textContent = 'Start frame';
      const start = document.createElement('input'); start.type = 'number'; start.min = 1; start.value = clip.start_frame + 1;
      start.onchange = () => updateAudioClip(clip.id, { start_frame: Math.max(0, Math.round(Number(start.value) || 1) - 1) });
      startRow.append(startLabel, start);
      const offsetRow = document.createElement('div'); offsetRow.className = 'xrow n';
      const offsetLabel = document.createElement('span'); offsetLabel.textContent = 'Trim offset';
      const offset = document.createElement('input'); offset.type = 'number'; offset.min = 0; offset.step = '0.01';
      offset.value = clip.offset_seconds || 0;
      offset.onchange = () => updateAudioClip(clip.id, { offset_seconds: Math.max(0, Number(offset.value) || 0) });
      offsetRow.append(offsetLabel, offset);
      row.append(startRow, offsetRow);
      row.append(makeControl('Volume', 0, 100, Math.round((clip.volume ?? 1) * 100), value => {
        updateAudioClip(clip.id, { volume: value / 100 });
      }));
      list.append(row);
    }

    function updateAudioClip(id, patch) {
      const next = (state.project.audio || []).map(item =>
        item.id === id ? { ...item, ...patch } : item);
      changeProjectArray('audio', next, 'Edit audio clip');
    }
  }

  async function uploadAudio() {
    const file = $('audioFile').files?.[0];
    if (!file) { toast('Choose an audio file first.', 'err'); return; }
    const button = $('audioUpload'); button.disabled = true;
    try {
      const result = await Audio.upload(state.projectId, file, {
        id: $('audioId').value.trim(),
        name: $('audioName').value.trim(),
        start_frame: Math.max(0, Number($('audioStart').value || state.frame + 1) - 1),
        offset_seconds: Math.max(0, Number($('audioOffset').value) || 0),
        volume: 1,
      });
      const clips = state.project.audio || [];
      const index = clips.findIndex(clip => clip.id === result.clip.id);
      const next = index < 0 ? [...clips, result.clip] : clips.map((clip, i) => i === index ? result.clip : clip);
      changeProjectArray('audio', next, 'Import audio clip');
      $('audioFile').value = '';
      toast(`Imported audio: ${result.clip.name}`, 'ok', 5000);
    } catch (error) {
      const details = error.details?.length ? `: ${error.details.slice(0, 4).join('; ')}` : '';
      toast(`${error.message}${details}`, 'err', 6000);
    } finally {
      button.disabled = false;
    }
  }

  function render() {
    if (!state.project) return;
    renderEffects();
    renderRig();
    renderCharacterList();
    renderAudio();
  }

  root.querySelectorAll('[data-studio-tab]').forEach(button => {
    button.onclick = () => showTab(button.dataset.studioTab);
  });
  $('effectAdd').onclick = addEffect;
  $('rigCharacter').onchange = event => { selectedCharacterId = event.target.value; renderRig(); };
  $('showRigOverlay').checked = state.showRigOverlay;
  $('showRigOverlay').onchange = event => setState({ showRigOverlay: event.target.checked });
  $('rigCreate').onclick = createRig;
  $('rigDelete').onclick = deleteRig;
  $('rigAuto').onclick = autoRig;
  $('rigWalkApply').onclick = applyWalkControls;
  $('rigTurnApply').onclick = applyTurnChoreography;
  for (const id of ['rigWalkStride', 'rigWalkBob', 'rigWalkWeight']) {
    $(id).addEventListener('input', () => {
      const value = Number($(id).value);
      const suffix = id === 'rigWalkWeight' ? value.toFixed(2) : String(value);
      const outputId = id === 'rigWalkStride' ? 'rigWalkStrideValue'
        : id === 'rigWalkBob' ? 'rigWalkBobValue' : 'rigWalkWeightValue';
      $(outputId).textContent = suffix;
    });
  }
  $('boneAdd').onclick = addBone;
  $('constraintBone').addEventListener('change', () => renderRotationLimitControls((state.project?.rigs || []).find(item => item.character_id === selectedCharacterId)));
  $('rotationLimitEnabled').addEventListener('change', () => {
    const active = $('rotationLimitEnabled').checked && !!$('constraintBone').value;
    $('rotationLimitMin').disabled = !active;
    $('rotationLimitMax').disabled = !active;
    if (active) $('rotationLimitStatus').textContent = 'Set a minimum and maximum, then apply the constraint.';
  });
  $('rotationLimitApply').onclick = applyRotationLimit;
  $('ikUpperBone').addEventListener('change', () => renderIKControls((state.project?.rigs || []).find(item => item.character_id === selectedCharacterId)));
  $('ikLowerBone').addEventListener('change', () => renderIKControls((state.project?.rigs || []).find(item => item.character_id === selectedCharacterId)));
  $('ikApply').onclick = applyIKTarget;
  $('ikRemove').onclick = removeIKTarget;
  $('skinWeight').oninput = event => { $('skinWeightValue').textContent = Number(event.target.value).toFixed(2); };
  $('skinAutoWeight').onclick = () => writeWeightedDrawing('auto');
  $('skinAssign').onclick = () => writeWeightedDrawing('assign');
  $('skinClear').onclick = () => writeWeightedDrawing('clear');
  $('skinBone')?.addEventListener('change', event => {
    setState({ weightBoneId: event.target.value || null });
    updateSkinStatus(`Weight paint target: ${event.target.selectedOptions[0]?.textContent || 'none'}`);
  });
  $('weightRadius')?.addEventListener('input', event => {
    $('weightRadiusValue').textContent = event.target.value;
  });
  bus.on('viewport:down', point => startWeightPaint(point));
  bus.on('viewport:move', point => paintAt(point));
  bus.on('viewport:up', () => finishWeightPaint(true));
  bus.on('viewport:cancel', () => finishWeightPaint(false));
  $('generateCharacter').onclick = generateCharacter;
  $('audioUpload').onclick = uploadAudio;
  bus.on('project:changed', render);
  bus.on('state', patch => {
    if ('project' in patch || 'sceneId' in patch) render();
  });
  showTab(activeTab);
  render();
  return { showTab, refresh: render };
}
