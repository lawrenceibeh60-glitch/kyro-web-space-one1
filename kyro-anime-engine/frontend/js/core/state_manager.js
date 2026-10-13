// frontend/js/core/state_manager.js - single shared editor state
import { bus } from './event_bus.js';

export const state = {
  project: null, projectId: null, sceneId: null, layerId: null,
  frame: 0, tool: 'brush', cameraMode: 'pan', dirty: false,
  loop: true, autokey: true, showRigOverlay: false, keyEase: 'ease_in_out', selKey: null, // selKey = {layerId, frame} chosen in the dope sheet
  view: { zoom: 1, panX: 0, panY: 0 },
  toolOpts: { color: '#111111', size: 4, opacity: 1, smoothing: 0.5, eraserSize: 16, greasePreset: 'pencil' },
  preview: null, // transient in-progress stroke / eraser feedback, never saved
};

export function setState(patch) {
  Object.assign(state, patch);
  bus.emit('state', patch);
}

export const getScene = () => state.project?.scenes.find(s => s.id === state.sceneId) ?? null;
export const getLayer = (id = state.layerId) => getScene()?.layers.find(l => l.id === id) ?? null;
export const sceneIndex = () => state.project.scenes.findIndex(s => s.id === state.sceneId);

export function getIn(obj, path) { return path.reduce((o, k) => o?.[k], obj); }
export function setIn(obj, path, value) {
  const parent = getIn(obj, path.slice(0, -1));
  const key = path[path.length - 1];
  if (value === undefined) delete parent[key]; else parent[key] = value;
}
