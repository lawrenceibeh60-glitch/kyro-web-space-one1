// Scene graph traversal and transform helpers. Legacy flat layer arrays remain valid.
import { evaluateTransform, evaluateOpacity } from '../animation/pose_evaluator.js';

const finite = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) : fallback;

/**
 * Flatten drawable leaves in paint order while preserving ancestor groups.
 * Group nodes are retained as drawable entries when they have exposures, then
 * their children are visited in order. Invisible ancestors suppress a subtree.
 */
export function flattenLayerTree(layers = [], ancestors = [], output = [], includeHidden = false) {
  for (const layer of Array.isArray(layers) ? layers : []) {
    if (!layer || (!includeHidden && layer.visible === false)) continue;
    const entry = { layer, ancestors: ancestors.slice() };
    output.push(entry);
    if (Array.isArray(layer.children) && layer.children.length) {
      flattenLayerTree(layer.children, [...ancestors, layer], output, includeHidden);
    }
  }
  return output;
}

export function indexLayerTree(layers = []) {
  const byId = new Map();
  for (const { layer, ancestors } of flattenLayerTree(layers, [], [])) {
    byId.set(layer.id, { layer, ancestors });
  }
  // Also index empty groups so they can be targeted by hierarchy tools.
  const visit = (nodes, ancestors = []) => {
    for (const layer of Array.isArray(nodes) ? nodes : []) {
      if (!layer || !layer.id) continue;
      if (!byId.has(layer.id)) byId.set(layer.id, { layer, ancestors: ancestors.slice() });
      visit(layer.children, [...ancestors, layer]);
    }
  };
  visit(layers);
  return byId;
}

export function findLayerLocation(layers, targetId) {
  const walk = (nodes, path = [], ancestors = []) => {
    for (let index = 0; index < (Array.isArray(nodes) ? nodes.length : 0); index++) {
      const layer = nodes[index];
      if (!layer) continue;
      const nextPath = [...path, index];
      if (layer.id === targetId) return { layer, container: nodes, index, path: nextPath, ancestors };
      const found = walk(layer.children || [], [...path, index, 'children'], [...ancestors, layer]);
      if (found) return found;
    }
    return null;
  };
  return walk(layers);
}

export function findLayerPath(layers, targetId) {
  const walk = (nodes, path) => {
    for (const layer of Array.isArray(nodes) ? nodes : []) {
      if (!layer) continue;
      const next = [...path, layer];
      if (layer.id === targetId) return next;
      const found = walk(layer.children, next);
      if (found) return found;
    }
    return null;
  };
  return walk(layers, []);
}

export function effectiveLayerOpacity(layer, ancestors = [], frame = 0) {
  return [...ancestors, layer].reduce((alpha, item) => alpha * evaluateOpacity(item, frame), 1);
}

/** Apply ancestor transforms in parent-to-child order. Caller owns save/restore. */
export function applyAncestorTransforms(ctx, ancestors = [], frame = 0) {
  for (const parent of ancestors) {
    const t = evaluateTransform(parent, frame);
    ctx.translate(finite(t.x, 0), finite(t.y, 0));
    ctx.rotate(finite(t.rotation, 0) * Math.PI / 180);
    ctx.scale(finite(t.scale_x, 1), finite(t.scale_y, 1));
    ctx.translate(-finite(t.anchor_x, 0), -finite(t.anchor_y, 0));
  }
}

export function worldTransformForLayer(layer, ancestors = [], frame = 0) {
  const path = [...ancestors, layer].filter(Boolean);
  // Affine 2D composition is represented as a matrix, preserving rotation and
  // non-uniform scale when groups are nested. The returned matrix is Canvas2D-compatible.
  let matrix = [1, 0, 0, 1, 0, 0];
  const multiply = (a, b) => [
    a[0] * b[0] + a[2] * b[1],
    a[1] * b[0] + a[3] * b[1],
    a[0] * b[2] + a[2] * b[3],
    a[1] * b[2] + a[3] * b[3],
    a[0] * b[4] + a[2] * b[5] + a[4],
    a[1] * b[4] + a[3] * b[5] + a[5],
  ];
  for (const item of path) {
    const t = evaluateTransform(item, frame);
    const angle = finite(t.rotation, 0) * Math.PI / 180;
    const sx = finite(t.scale_x, 1), sy = finite(t.scale_y, 1);
    const c = Math.cos(angle), s = Math.sin(angle);
    const x = finite(t.x, 0), y = finite(t.y, 0);
    const ax = finite(t.anchor_x, 0), ay = finite(t.anchor_y, 0);
    matrix = multiply(matrix, [c * sx, s * sx, -s * sy, c * sy, x + ax * (1 - c * sx) + ay * s * sy, y - ax * s * sx + ay * (1 - c * sy)]);
  }
  return { x: matrix[4], y: matrix[5], rotation: Math.atan2(matrix[1], matrix[0]) * 180 / Math.PI,
    scale_x: Math.hypot(matrix[0], matrix[1]), scale_y: Math.hypot(matrix[2], matrix[3]), matrix };
}

/** Move a layer within its current parent, rejecting cycles and invalid destinations. */
export function reparentLayer(layers, layerId, parentId = null, index = Infinity) {
  const roots = Array.isArray(layers) ? layers.map(layer => ({ ...layer })) : [];
  const cloneChildren = layer => ({ ...layer, ...(Array.isArray(layer.children) ? { children: layer.children.map(cloneChildren) } : {}) });
  const tree = roots.map(cloneChildren);
  const findContainer = (nodes, id, parent = null) => {
    for (const node of nodes) {
      if (node.id === id) return { nodes, node, parent };
      const found = findContainer(node.children || [], id, node);
      if (found) return found;
    }
    return null;
  };
  const source = findContainer(tree, layerId);
  if (!source) throw new Error('Layer not found: ' + layerId);
  if (parentId === layerId || (parentId && findLayerPath([source.node], parentId))) throw new Error('Cannot move a layer into its own subtree');
  const destination = parentId ? findContainer(tree, parentId) : { node: null, nodes: tree };
  if (!destination || (destination.node && destination.node.type !== 'group' && destination.node.type !== 'character_instance')) {
    throw new Error('Destination must be a group layer');
  }
  source.nodes.splice(source.nodes.indexOf(source.node), 1);
  const siblings = destination.node ? (destination.node.children ||= []) : destination.nodes;
  const at = Math.max(0, Math.min(siblings.length, Number.isFinite(index) ? Math.trunc(index) : siblings.length));
  siblings.splice(at, 0, source.node);
  return tree;
}
