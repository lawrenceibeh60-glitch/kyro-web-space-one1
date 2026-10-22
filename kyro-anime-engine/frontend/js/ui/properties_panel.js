// frontend/js/ui/properties_panel.js - Properties tabs (Tool / Object / Output / JSON / Prefs) and the Output tab.
import { bus } from '../core/event_bus.js';
import { state, setState } from '../core/state_manager.js';
import { execute, setValue } from '../core/command_manager.js';
import { Projects } from '../api/projects.js';
import { Characters } from '../api/characters.js';
import { mergeProjectAdditively } from '../api/project_import.js';
import { Timeline } from '../api/timeline.js';
import { evaluateCamera } from '../animation/camera_evaluator.js';
import { toast } from './notifications.js';

const TABS = ['tool', 'object', 'output', 'json', 'prefs'];
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

function safeJsonText(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch (_) { return ''; }
}

export function initPropertiesPanel({ fit, openExport, onProjectReplaced, onProjectUpdated }) {
  const $ = id => document.getElementById(id);
  const root = $('p-properties');
  let current = 'tool';

  function showTab(name) {
    if (!TABS.includes(name)) return;
    const changedTab = current !== name;
    current = name;
    root.querySelectorAll('.ptab').forEach(b => b.classList.toggle('on', b.dataset.tab === name));
    root.querySelectorAll('[data-pane]').forEach(p => { p.hidden = p.dataset.pane !== name; });
    refresh();
    if (changedTab && name === 'json') refreshJsonText();
  }

  function refresh() {
    if (!state.project) return;
    const s = state.project.settings;
    const put = (id, v) => { const el = $(id); if (document.activeElement !== el) el.value = v; };
    put('o_w', s.width); put('o_h', s.height); put('o_fps', s.fps); put('o_end', s.duration_frames);
    put('o_bg', (s.background || '#ffffff').slice(0, 7));
    const scene = state.project.scenes.find(item => item.id === state.sceneId) || state.project.scenes[0];
    const camera = evaluateCamera(scene?.camera, state.frame);
    put('cam_x', camera.x); put('cam_y', camera.y);
    put('cam_rotation', camera.rotation);
    put('cam_zoom', Math.round(camera.zoom * 100));
    $('cam_zoomV').textContent = `${(camera.zoom * 100).toFixed(0)}%`;
    const selectedLayer = scene?.layers?.find(layer => layer.id === state.layerId);
    const clipArea = $('layerClipPath');
    if (clipArea && document.activeElement !== clipArea) {
      clipArea.value = selectedLayer?.clip_path ? safeJsonText(selectedLayer.clip_path) : '';
    }
    const depth = selectedLayer?.depth ?? 1;
    put('layerDepth', Math.round(depth * 100));
    $('layerDepthV').textContent = `${Math.round(depth * 100)}%`;
    const lightSelect = $('lightSelect');
    const lights = scene?.lights || [];
    const selectedLightId = lightSelect.value;
    lightSelect.replaceChildren(...lights.map((light, index) => {
      const option = document.createElement('option');
      option.value = light.id;
      option.textContent = `Light ${index + 1}`;
      return option;
    }));
    if (lights.some(light => light.id === selectedLightId)) lightSelect.value = selectedLightId;
    const light = lights.find(item => item.id === lightSelect.value) || lights[0];
    if (light && !lightSelect.value) lightSelect.value = light.id;
    for (const id of ['lightSelect', 'lightDelete', 'light_x', 'light_y', 'light_radius', 'light_intensity', 'light_color']) {
      $(id).disabled = !light && id !== 'lightSelect';
    }
    if (light) {
      put('light_x', light.x); put('light_y', light.y);
      put('light_radius', light.radius);
      put('light_intensity', Math.round(light.intensity * 100));
      put('light_color', light.color);
      $('light_radiusV').textContent = `${light.radius}px`;
      $('light_intensityV').textContent = `${Math.round(light.intensity * 100)}%`;
    } else {
      $('light_radiusV').textContent = '-';
      $('light_intensityV').textContent = '-';
    }
    const layerArea = $('layerJson');
    if (current === 'json' && layerArea && document.activeElement !== layerArea) {
      const scenes = state.project.scenes || [];
      const scene = scenes.find(s => s.id === state.sceneId) || scenes[0];
      const layers = scene?.layers || [];
      const layer = layers.find(l => l.id === state.layerId) || layers[layers.length - 1];
      layerArea.value = safeJsonText(layer || {});
    }
  }

  function refreshJsonText() {
    const area = $('jsonText');
    if (area && state.project && document.activeElement !== area) {
      area.value = safeJsonText(state.project);
      $('jsonStatus').textContent = '';
    }
  }

  async function replaceProjectFromJson(payload) {
    try {
      if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
        throw new Error('Project JSON must be an object');
      }
      if (payload.format === 'kae-character') {
        if (!state.projectId) throw new Error('Open a project before importing a character');
        const result = await Characters.import(state.projectId, payload);
        onProjectUpdated?.();
        const currentScene = result.project.scenes.find(scene => scene.id === state.sceneId);
        const scene = currentScene?.layers.some(layer => layer.character_id === result.character.id)
          ? currentScene
          : result.project.scenes.find(item => item.layers.some(layer => layer.character_id === result.character.id));
        const layer = scene?.layers.find(item => item.character_id === result.character.id);
        setState({
          project: result.project,
          sceneId: scene?.id ?? result.project.scenes[0]?.id,
          layerId: layer?.id ?? null,
          frame: Math.min(state.frame, result.project.settings.duration_frames - 1),
          dirty: false,
        });
        bus.emit('project:changed');
        toast(`Imported ${result.character.name} (${result.character.id}) · ${result.character.parts.length} part(s)`, 'ok', 5000);
        return true;
      }
      if (!confirm('Replace the open project with this JSON? This saves the replacement to the current project.')) return;
      const next = { ...payload, id: state.projectId };
      const saved = await Projects.save(state.projectId, next);
      onProjectReplaced(saved);
      showTab('json');
      toast('Project imported and opened', 'ok');
      return true;
    } catch (e) {
      const details = e.details?.length ? ': ' + e.details.slice(0, 4).join('; ') : '';
      toast((e?.message || 'Invalid project JSON') + details, 'err', 6000);
      return false;
    }
  }

  async function importJsonFiles(files) {
    if (!files.length) return;
    const documents = [];
    try {
      for (const file of files) {
        const payload = JSON.parse(await file.text());
        if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
          throw new Error(`${file.name}: JSON document must be an object`);
        }
        documents.push({ file, payload });
      }
    } catch (e) {
      toast(e?.message || 'Invalid JSON file', 'err', 6000);
      return;
    }
    const unsupported = documents.find(({ payload }) =>
      payload.format !== 'kae' && payload.format !== 'kae-character');
    if (unsupported) {
      toast(`${unsupported.file.name}: expected a "kae" project or "kae-character" document`, 'err', 6000);
      return;
    }

    const projectDocuments = documents.filter(item => item.payload.format === 'kae');
    const characterDocuments = documents.filter(item => item.payload.format === 'kae-character');
    const differentSetups = projectDocuments.filter(({ payload }) =>
      payload.id !== state.projectId
      || ['width', 'height', 'fps'].some(key =>
        payload.settings?.[key] !== state.project.settings?.[key]));
    if (differentSetups.length) {
      const descriptions = differentSetups.map(({ file, payload }) =>
        `- ${file.name} (${payload.name || payload.id || 'unnamed project'})`).join('\n');
      const message = `These files come from a different project identity or canvas setup:\n${descriptions}\n\nMerge only new, non-conflicting components into "${state.project.name}"? Existing components will be kept.`;
      if (!confirm(message)) {
        toast('JSON import cancelled; no files were imported.', 'info', 5000);
        return;
      }
    }

    let projectImported = 0;
    let characterImported = 0;
    let characterSkipped = 0;
    const totals = { drawings: 0, scenes: 0, layers: 0, lights: 0, characters: 0, effects: 0, rigs: 0, palette: 0 };
    const skipped = { drawings: 0, scenes: 0, layers: 0, lights: 0, characters: 0, effects: 0, rigs: 0, audio: 0 };

    try {
      if (projectDocuments.length) {
        let merged = state.project;
        for (const { payload } of projectDocuments) {
          const result = mergeProjectAdditively(merged, payload);
          merged = result.project;
          for (const [key, count] of Object.entries(result.added)) totals[key] += count;
          for (const [key, count] of Object.entries(result.skipped)) skipped[key] += count;
        }
        const addedCount = Object.values(totals).reduce((sum, count) => sum + count, 0);
        if (addedCount) {
          const saved = await Projects.save(state.projectId, merged);
          onProjectReplaced(saved);
          projectImported = projectDocuments.length;
        }
      }

      for (const { file, payload } of characterDocuments) {
        if ((state.project.characters || []).some(character => character.id === payload.id)) {
          characterSkipped++;
          continue;
        }
        try {
          const result = await Characters.import(state.projectId, payload);
          onProjectUpdated?.();
          const scene = result.project.scenes.find(item =>
            item.layers.some(layer => layer.character_id === result.character.id));
          const layer = scene?.layers.find(item => item.character_id === result.character.id);
          setState({
            project: result.project,
            sceneId: scene?.id ?? result.project.scenes[0]?.id,
            layerId: layer?.id ?? null,
            frame: Math.min(state.frame, result.project.settings.duration_frames - 1),
            dirty: false,
          });
          bus.emit('project:changed');
          characterImported++;
        } catch (error) {
          const details = error.details?.length ? ': ' + error.details.slice(0, 4).join('; ') : '';
          toast(`${file.name}: ${error.message}${details}`, 'err', 6000);
        }
      }
    } catch (e) {
      const details = e.details?.length ? ': ' + e.details.slice(0, 4).join('; ') : '';
      toast((e?.message || 'Could not merge imported project JSON') + details, 'err', 6000);
      return;
    }

    const totalImported = projectImported + characterImported;
    if (!totalImported) {
      toast(Object.values(skipped).some(count => count)
        ? 'No new components were added; existing data was preserved.'
        : 'No importable project components were found.', 'info', 5000);
      return;
    }
    const summary = Object.entries(totals)
      .filter(([, count]) => count)
      .map(([name, count]) => `${count} ${name}`)
      .join(', ');
    const audioNote = skipped.audio
      ? ` Audio metadata for ${skipped.audio} new clip(s) was skipped because JSON files do not include audio bytes.`
      : '';
    const skippedCount = Object.values(skipped).reduce((sum, count) => sum + count, 0) + characterSkipped;
    toast(
      `Merged ${projectImported} project file(s) and imported ${characterImported} character file(s)${summary ? `; added ${summary}` : ''}${skippedCount ? `; kept ${skippedCount} existing/conflicting component(s)` : ''}.${audioNote}`,
      'ok',
      8000,
    );
  }

  async function applyJsonString() {
    const area = $('jsonText');
    if (!area) return;
    try {
      const parsed = JSON.parse(area.value);
      await replaceProjectFromJson(parsed);
    } catch (e) {
      toast(e?.message || 'Invalid project JSON', 'err');
    }
  }

  async function applyCharacterJsonString() {
    const area = $('jsonText');
    if (!area) return;
    try {
      const parsed = JSON.parse(area.value);
      if (parsed?.format !== 'kae-character') {
        throw new Error('Character JSON must use format "kae-character"');
      }
      await replaceProjectFromJson(parsed);
    } catch (e) {
      const details = e.details?.length ? ': ' + e.details.slice(0, 4).join('; ') : '';
      toast((e?.message || 'Invalid character JSON') + details, 'err', 6000);
    }
  }

  function downloadJson() {
    const area = $('jsonText');
    if (!area) return;
    const blob = new Blob([safeJsonText(state.project)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (state.project?.name || 'project') + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function applyLayerPatch() {
    const area = $('layerJson');
    if (!area || !state.project) return;
    try {
      const patch = JSON.parse(area.value);
      const scenes = state.project.scenes || [];
      const scene = scenes.find(s => s.id === state.sceneId) || scenes[0];
      if (!scene) throw new Error('No scene selected');
      const layers = scene.layers || [];
      const idx = layers.findIndex(l => l.id === state.layerId);
      const layer = idx >= 0 ? layers[idx] : layers[layers.length - 1];
      if (!layer) throw new Error('No layer selected');
      if (!patch || typeof patch !== 'object' || Array.isArray(patch)) throw new Error('Layer patch must be an object');
      Object.assign(layer, patch);
      setState({ project: state.project, dirty: true });
      refresh();
      toast('Layer patch applied', 'ok');
    } catch (e) {
      toast(e?.message || 'Invalid layer patch JSON', 'err');
    }
  }

  async function applyScript() {
    const area = $('scriptJson');
    if (!area || !state.projectId) return;
    try {
      const script = JSON.parse(area.value);
      if (!script || typeof script !== 'object' || !Array.isArray(script.ops)) {
        throw new Error('Timeline script must be an object with an ops array');
      }
      const result = await Timeline.applyScript(state.projectId, script);
      const fresh = await Projects.get(state.projectId);
      setState({ project: fresh, dirty: false, frame: Math.min(state.frame, fresh.settings.duration_frames - 1) });
      toast(`Timeline script applied: ${result.applied} op(s)`, 'ok');
      refresh();
    } catch (e) {
      toast(e?.message || 'Invalid timeline script JSON', 'err');
    }
  }

  function writeSampleScript() {
    const area = $('scriptJson');
    if (!area) return;
    const scene = state.project?.scenes?.[0];
    const layer = scene?.layers?.[0];
    area.value = JSON.stringify({
      ops: [
        { op: 'set_key', scene_id: scene?.id || 'scene_1', layer_id: layer?.id || 'layer_1', channel: 'x', time: 0, value: 0, ease: 'linear' },
        { op: 'set_key', scene_id: scene?.id || 'scene_1', layer_id: layer?.id || 'layer_1', channel: 'x', time: 12, value: 200, ease: 'ease_in_out' },
      ],
    }, null, 2);
  }

  const setting = (key, v, label) => { if (state.project.settings[key] !== v) execute(setValue(['settings', key], v, label)); };
  function setCameraTransform(key, value) {
    const index = state.project.scenes.findIndex(item => item.id === state.sceneId);
    if (index < 0) return;
    const current = state.project.scenes[index].camera || {};
    const frame = state.frame;
    const tracks = { ...(current.tracks || {}) };
    if (tracks[key]?.length) {
      const keyframes = [...tracks[key]];
      const valueAtFrame = { t: frame, v: value, ease: state.keyEase || 'linear' };
      const existing = keyframes.findIndex(item => item.t === frame);
      if (existing >= 0) keyframes[existing] = valueAtFrame;
      else keyframes.push(valueAtFrame);
      keyframes.sort((a, b) => a.t - b.t);
      tracks[key] = keyframes;
    }
    const camera = {
      ...current,
      tracks,
      transform: { x: 0, y: 0, scale_x: 1, scale_y: 1, ...(current.transform || {}), [key]: value },
    };
    execute(setValue(['scenes', index, 'camera'], camera, 'Camera'));
  }
  function keyCamera() {
    const index = state.project.scenes.findIndex(item => item.id === state.sceneId);
    if (index < 0) return;
    const current = state.project.scenes[index].camera || {};
    const evaluated = evaluateCamera(current, state.frame);
    const transform = {
      ...(current.transform || {}),
      x: evaluated.x, y: evaluated.y, rotation: evaluated.rotation, scale_x: evaluated.zoom,
    };
    const frame = state.frame;
    const tracks = { ...(current.tracks || {}) };
    for (const channel of ['x', 'y', 'rotation', 'scale_x']) {
      const keyframes = [...(tracks[channel] || [])];
      const key = { t: frame, v: transform[channel], ease: state.keyEase || 'linear' };
      const existing = keyframes.findIndex(item => item.t === frame);
      if (existing >= 0) keyframes[existing] = key;
      else keyframes.push(key);
      keyframes.sort((a, b) => a.t - b.t);
      tracks[channel] = keyframes;
    }
    execute(setValue(['scenes', index, 'camera'], { ...current, transform, tracks }, 'Key Camera'));
    toast(`Camera keyed at frame ${frame + 1}`, 'ok');
  }
  function selectedSceneIndex() {
    return state.project.scenes.findIndex(item => item.id === state.sceneId);
  }
  function selectedLightIndex(scene) {
    return (scene?.lights || []).findIndex(light => light.id === $('lightSelect').value);
  }
  function setLightValue(key, value) {
    const sceneIndex = selectedSceneIndex();
    const scene = state.project.scenes[sceneIndex];
    const lightIndex = selectedLightIndex(scene);
    if (sceneIndex < 0 || lightIndex < 0) return;
    execute(setValue(['scenes', sceneIndex, 'lights', lightIndex, key], value, 'Edit light'));
  }
  $('o_w').onchange = e => { setting('width', clamp(Math.round(+e.target.value) || 1280, 16, 8192), 'Resolution'); fit(); refresh(); };
  $('o_h').onchange = e => { setting('height', clamp(Math.round(+e.target.value) || 720, 16, 8192), 'Resolution'); fit(); refresh(); };
  $('o_fps').onchange = e => { setting('fps', clamp(+e.target.value || 12, 1, 120), 'Frame rate'); refresh(); };
  $('o_end').onchange = e => {
    setting('duration_frames', clamp(Math.round(+e.target.value) || 1, 1, 2000), 'Frame end');
    if (state.frame > state.project.settings.duration_frames - 1) state.frame = state.project.settings.duration_frames - 1;
    refresh();
  };
  $('o_bg').onchange = e => { setting('background', e.target.value, 'Background'); };
  $('cam_x').onchange = e => { setCameraTransform('x', clamp(Math.round(+e.target.value) || 0, -8192, 8192)); refresh(); };
  $('cam_y').onchange = e => { setCameraTransform('y', clamp(Math.round(+e.target.value) || 0, -8192, 8192)); refresh(); };
  $('cam_rotation').onchange = e => { setCameraTransform('rotation', clamp(Math.round(+e.target.value) || 0, -3600, 3600)); refresh(); };
  $('cam_zoom').oninput = e => { $('cam_zoomV').textContent = `${(+e.target.value).toFixed(0)}%`; };
  $('cam_zoom').onchange = e => { setCameraTransform('scale_x', clamp((+e.target.value || 100) / 100, 0.05, 32)); refresh(); };
  $('cam_key').onclick = keyCamera;
  $('lightSelect').onchange = refresh;
  $('lightAdd').onclick = () => {
    const sceneIndex = selectedSceneIndex();
    if (sceneIndex < 0) return;
    const scene = state.project.scenes[sceneIndex];
    const lights = scene.lights || [];
    const { width, height } = state.project.settings;
    const light = {
      id: `light_${Date.now().toString(36)}`,
      x: Math.round(width / 2), y: Math.round(height / 2),
      radius: 480, intensity: 0.7, color: '#ffd9a0',
    };
    execute(setValue(['scenes', sceneIndex, 'lights'], [...lights, light], 'Add light'));
    $('lightSelect').value = light.id;
    refresh();
  };
  $('lightDelete').onclick = () => {
    const sceneIndex = selectedSceneIndex();
    const scene = state.project.scenes[sceneIndex];
    const lightIndex = selectedLightIndex(scene);
    if (sceneIndex < 0 || lightIndex < 0) return;
    execute(setValue(['scenes', sceneIndex, 'lights'], scene.lights.filter((_, i) => i !== lightIndex), 'Remove light'));
    refresh();
  };
  $('light_x').onchange = e => setLightValue('x', clamp(Math.round(+e.target.value) || 0, -8192, 8192));
  $('light_y').onchange = e => setLightValue('y', clamp(Math.round(+e.target.value) || 0, -8192, 8192));
  $('light_radius').oninput = e => { $('light_radiusV').textContent = `${e.target.value}px`; };
  $('light_radius').onchange = e => setLightValue('radius', clamp(Math.round(+e.target.value), 16, 8192));
  $('light_intensity').oninput = e => { $('light_intensityV').textContent = `${e.target.value}%`; };
  $('light_intensity').onchange = e => setLightValue('intensity', clamp(+e.target.value / 100, 0, 1));
  $('light_color').onchange = e => setLightValue('color', e.target.value);
  $('layerDepth').oninput = e => { $('layerDepthV').textContent = `${e.target.value}%`; };
  $('layerDepth').onchange = e => {
    const sceneIndex = state.project.scenes.findIndex(item => item.id === state.sceneId);
    const layerIndex = state.project.scenes[sceneIndex]?.layers.findIndex(layer => layer.id === state.layerId) ?? -1;
    if (sceneIndex < 0 || layerIndex < 0) return;
    execute(setValue(['scenes', sceneIndex, 'layers', layerIndex, 'depth'], clamp(+e.target.value / 100, 0, 2), 'Layer depth'));
    refresh();
  };
  $('o_fit').onclick = fit;
  $('o_importJson').onclick = () => $('jsonImportFile').click();
  $('o_export').onclick = openExport;
  $('jsonReload').onclick = refreshJsonText;
  $('jsonImportEditor').onclick = () => $('jsonImportFile').click();
  $('jsonApply').onclick = applyJsonString;
  $('jsonCharacterApply').onclick = applyCharacterJsonString;
  $('jsonDownload').onclick = downloadJson;
  $('layerRefresh').onclick = () => { const area = $('layerJson'); if (area) area.value = safeJsonText((state.project?.scenes || []).find(s => s.id === state.sceneId)?.layers?.find(l => l.id === state.layerId) || {}); };
  $('layerApply').onclick = applyLayerPatch;
  function applyLayerClipPath(clear = false) {
    if (!state.project) return;
    const sceneIndex = state.project.scenes.findIndex(item => item.id === state.sceneId);
    const scene = state.project.scenes[sceneIndex];
    const layerIndex = scene?.layers?.findIndex(item => item.id === state.layerId) ?? -1;
    const area = $('layerClipPath');
    if (sceneIndex < 0 || layerIndex < 0 || !area) {
      toast('Select a top-level layer before editing its clip path.', 'err');
      return;
    }
    const nextLayer = { ...scene.layers[layerIndex] };
    if (clear) {
      delete nextLayer.clip_path;
    } else {
      let commands;
      try { commands = JSON.parse(area.value); }
      catch (_) { toast('Clip path must be valid JSON.', 'err'); return; }
      const arity = { M: 3, L: 3, Q: 5, C: 7, Z: 1 };
      if (!Array.isArray(commands) || commands.length < 2
          || commands[0]?.[0] !== 'M'
          || commands.some(command => !Array.isArray(command)
            || !Object.prototype.hasOwnProperty.call(arity, command[0])
            || command.length !== arity[command[0]]
            || (command[0] === 'M' && commands.indexOf(command) !== 0)
            || command.slice(1).some(value => typeof value !== 'number' || !Number.isFinite(value)))) {
        toast('Clip path needs an M command followed by valid L, Q, C or Z commands.', 'err');
        return;
      }
      nextLayer.clip_path = commands;
    }
    execute(setValue(['scenes', sceneIndex, 'layers', layerIndex], nextLayer,
      clear ? 'Clear clipping path' : 'Edit clipping path'));
    $('layerClipStatus').textContent = clear ? 'Clipping path removed.' : `Clip path applied (${nextLayer.clip_path.length} commands).`;
    toast(clear ? 'Clipping path cleared' : 'Clipping path applied', 'ok');
  }
  $('layerClipApply').onclick = () => applyLayerClipPath(false);
  $('layerClipClear').onclick = () => applyLayerClipPath(true);
  $('scriptSample').onclick = writeSampleScript;
  $('scriptApply').onclick = applyScript;
  $('jsonImportFile').onchange = async e => {
    const files = [...(e.target.files || [])];
    if (files.length) { await importJsonFiles(files); e.target.value = ''; }
  };
  root.querySelectorAll('.ptab').forEach(b => { b.onclick = () => showTab(b.dataset.tab); });

  bus.on('project:changed', () => {
    refresh();
    if (current === 'json') $('jsonStatus').textContent = 'Project changed. Use Reload to refresh this JSON snapshot.';
  });
  bus.on('state', p => {
    if ('project' in p || 'sceneId' in p) refresh();
    if ('project' in p && current === 'json') {
      $('jsonStatus').textContent = 'Project changed. Use Reload to refresh this JSON snapshot.';
    }
  });
  showTab('tool');
  return { showTab, refresh, current: () => current };
}
