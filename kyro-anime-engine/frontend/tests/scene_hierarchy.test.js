import test from 'node:test';
import assert from 'node:assert/strict';
import {
  flattenLayerTree, findLayerPath, indexLayerTree, effectiveLayerOpacity,
  worldTransformForLayer, reparentLayer,
} from '../js/scene/scene_hierarchy.js';
import { createDrawingLayer, createGroupLayer, nextLayerId, removeLayerFromTree, updateLayerTree } from '../js/scene/layers.js';

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
  assert.deepEqual(flattened.map(entry => entry.layer.id), ['background', 'character', 'body', 'faceGroup', 'mouth']);
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
  assert.deepEqual(moved[0].children.map(layer => layer.id), ['background', 'body', 'faceGroup']);
  assert.equal(tree[0].id, 'background');
  assert.throws(() => reparentLayer(tree, 'character', 'faceGroup'), /own subtree/);
  assert.throws(() => reparentLayer(tree, 'background', 'body'), /Destination must be a group/);
});

test('layer factories avoid collisions with hidden nested layers and apply safe defaults', () => {
  const layers = [{ id: 'layer_1', type: 'drawing', visible: false }, { id: 'group_1', type: 'group', children: [{ id: 'layer_2', type: 'drawing' }] }];
  assert.equal(nextLayerId(layers, 'layer'), 'layer_3');
  const drawing = createDrawingLayer(layers);
  assert.equal(drawing.id, 'layer_3');
  assert.equal(drawing.opacity, 1);
  const group = createGroupLayer(layers);
  assert.equal(group.id, 'group_2');
  assert.deepEqual(group.children, []);
});

test('immutable layer tree update and removal target nested layers without mutating source', () => {
  const source = [{ id: 'g', type: 'group', children: [{ id: 'l', type: 'drawing', visible: true }] }];
  const updated = updateLayerTree(source, 'l', { visible: false, name: 'Hidden' });
  assert.equal(updated[0].children[0].visible, false);
  assert.equal(source[0].children[0].visible, true);
  const removed = removeLayerFromTree(updated, 'l');
  assert.equal(removed.removed.id, 'l');
  assert.deepEqual(removed.layers[0].children, []);
  assert.deepEqual(updated[0].children.map(layer => layer.id), ['l']);
});
