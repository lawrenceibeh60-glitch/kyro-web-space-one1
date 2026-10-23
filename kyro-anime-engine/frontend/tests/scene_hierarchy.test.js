import test from 'node:test';
import assert from 'node:assert/strict';
import {
  flattenLayerTree, findLayerPath, indexLayerTree, effectiveLayerOpacity,
  worldTransformForLayer, reparentLayer,
} from '../js/scene/scene_hierarchy.js';

const tree = [
  { id: 'background', type: 'drawing', exposures: [{ start: 0, length: 1, drawing: 'bg' }] },
  { id: 'character', type: 'group', transform: { x: 100, y: 20, rotation: 90, scale_x: 2, scale_y: 2 }, opacity: 0.5, children: [
    { id: 'body', type: 'drawing', transform: { x: 10, y: 0 }, opacity: 0.8, exposures: [{ start: 0, length: 1, drawing: 'body' }] },
    { id: 'faceGroup', type: 'group', children: [
      { id: 'eyes', type: 'drawing', visible: false, exposures: [{ start: 0, length: 1, drawing: 'eyes' }] },
      { id: 'mouth', type: 'drawing', exposures: [{ start: 0, length: 1, drawing: 'mouth' }] },
    ] },
  ] },
];

test('flattenLayerTree preserves paint order and ancestor paths while excluding hidden subtrees', () => {
  const flattened = flattenLayerTree(tree);
  assert.deepEqual(flattened.map(entry => entry.layer.id), ['background', 'body', 'mouth']);
  assert.deepEqual(flattened.find(entry => entry.layer.id === 'mouth').ancestors.map(layer => layer.id), ['character', 'faceGroup']);
});

test('layer index and path resolution include empty groups', () => {
  const index = indexLayerTree(tree);
  assert.equal(index.get('faceGroup').layer.id, 'faceGroup');
  assert.deepEqual(findLayerPath(tree, 'mouth').map(layer => layer.id), ['character', 'faceGroup', 'mouth']);
  assert.equal(findLayerPath(tree, 'missing'), null);
});

test('nested opacity multiplies parent and child opacity', () => {
  assert.ok(Math.abs(effectiveLayerOpacity(tree[1].children[0], [tree[1]], 0) - 0.4) < 1e-9);
});

test('world transform composes parent translation, rotation, and child offset', () => {
  const world = worldTransformForLayer(tree[1].children[0], [tree[1]], 0);
  assert.ok(Math.abs(world.x - 100) < 1e-8);
  assert.ok(Math.abs(world.y - 40) < 1e-8);
  assert.ok(Math.abs(world.rotation - 90) < 1e-8);
  assert.ok(Math.abs(world.scale_x - 2) < 1e-8);
});

test('reparentLayer moves a layer into a group immutably and rejects cycles', () => {
  const moved = reparentLayer(tree, 'background', 'character', 0);
  assert.deepEqual(moved[1].children.map(layer => layer.id), ['background', 'body', 'faceGroup']);
  assert.equal(tree[0].id, 'background');
  assert.throws(() => reparentLayer(tree, 'character', 'faceGroup'), /own subtree/);
  assert.throws(() => reparentLayer(tree, 'background', 'body'), /Destination must be a group/);
});
