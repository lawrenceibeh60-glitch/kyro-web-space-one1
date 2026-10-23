// Immutable scene-layer domain helpers shared by editor tools and import workflows.
import { flattenLayerTree, findLayerLocation, reparentLayer } from './scene_hierarchy.js';

export { flattenLayerTree, findLayerLocation, reparentLayer };

export function nextLayerId(layers, prefix = 'layer') {
  const used = new Set(flattenLayerTree(layers || [], [], [], true).map(({ layer }) => layer.id));
  let index = 1;
  while (used.has(prefix + '_' + index)) index++;
  return prefix + '_' + index;
}

export function createDrawingLayer(layers, options = {}) {
  const id = options.id || nextLayerId(layers, 'layer');
  return {
    id,
    name: options.name || 'Layer ' + id.split('_').pop(),
    type: 'drawing',
    visible: options.visible !== false,
    locked: options.locked === true,
    opacity: Number.isFinite(options.opacity) ? Math.max(0, Math.min(1, options.opacity)) : 1,
    depth: Number.isFinite(options.depth) ? Math.max(0, Math.min(2, options.depth)) : 1,
    exposures: [],
    ...(options.transform ? { transform: { ...options.transform } } : {}),
  };
}

export function createGroupLayer(layers, options = {}) {
  const id = options.id || nextLayerId(layers, 'group');
  return {
    id,
    name: options.name || 'Group ' + id.split('_').pop(),
    type: 'group',
    visible: options.visible !== false,
    locked: options.locked === true,
    opacity: Number.isFinite(options.opacity) ? Math.max(0, Math.min(1, options.opacity)) : 1,
    transform: { x: 0, y: 0, rotation: 0, scale_x: 1, scale_y: 1, anchor_x: 0, anchor_y: 0, ...(options.transform || {}) },
    children: Array.isArray(options.children) ? options.children.map(cloneLayer) : [],
  };
}

function cloneLayer(layer) {
  return { ...layer, ...(Array.isArray(layer.children) ? { children: layer.children.map(cloneLayer) } : {}) };
}

export function updateLayerTree(layers, layerId, update) {
  let found = false;
  const visit = nodes => (Array.isArray(nodes) ? nodes : []).map(layer => {
    if (!layer) return layer;
    if (layer.id === layerId) {
      found = true;
      return typeof update === 'function' ? update(cloneLayer(layer)) : { ...cloneLayer(layer), ...update };
    }
    if (Array.isArray(layer.children)) return { ...layer, children: visit(layer.children) };
    return layer;
  });
  const result = visit(layers);
  if (!found) throw new Error('Layer not found: ' + layerId);
  return result;
}

export function removeLayerFromTree(layers, layerId) {
  const location = findLayerLocation(layers, layerId);
  if (!location) return { layers: (layers || []).map(cloneLayer), removed: null };
  const next = (layers || []).map(cloneLayer);
  const clonedLocation = findLayerLocation(next, layerId);
  const removed = clonedLocation.container.splice(clonedLocation.index, 1)[0];
  return { layers: next, removed };
}
