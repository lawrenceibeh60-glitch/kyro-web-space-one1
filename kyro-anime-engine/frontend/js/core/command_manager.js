// frontend/js/core/command_manager.js
// Every project edit goes through execute(cmd). A command is { label, do(), undo() }.
// Paths are arrays of keys into state.project, e.g. ['scenes', 0, 'layers', 1, 'visible'].
import { bus } from './event_bus.js';
import { state, setState, getIn, setIn } from './state_manager.js';
import { history } from './undo_redo.js';

const clone = v => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));

function changed(cmd) {
  setState({ dirty: true });
  bus.emit('project:changed', { label: cmd.label });
}

export function execute(cmd) { cmd.do(); history.push(cmd); changed(cmd); return cmd; }
export function undo() { const c = history.undo(); if (c) { c.undo(); changed(c); } }
export function redo() { const c = history.redo(); if (c) { c.do(); changed(c); } }

export function setValue(path, value, label = 'Edit') {
  let old;
  return {
    label,
    do() { old = getIn(state.project, path); setIn(state.project, path, clone(value)); },
    undo() { setIn(state.project, path, old); },
  };
}

export function insertAt(arrayPath, index, value, label = 'Insert') {
  return {
    label,
    do() { getIn(state.project, arrayPath).splice(index, 0, clone(value)); },
    undo() { getIn(state.project, arrayPath).splice(index, 1); },
  };
}

export function removeAt(arrayPath, index, label = 'Remove') {
  let removed;
  return {
    label,
    do() { removed = getIn(state.project, arrayPath).splice(index, 1)[0]; },
    undo() { getIn(state.project, arrayPath).splice(index, 0, removed); },
  };
}

export function batch(cmds, label = 'Batch') {
  return {
    label,
    do() { cmds.forEach(c => c.do()); },
    undo() { [...cmds].reverse().forEach(c => c.undo()); },
  };
}

// ---- layer animation state (transform / tracks / opacity) as one undoable unit ----
export function findLayer(id) {
  const visit = layers => {
    for (const layer of Array.isArray(layers) ? layers : []) {
      if (layer?.id === id) return layer;
      const nested = visit(layer?.children);
      if (nested) return nested;
    }
    return null;
  };
  for (const scene of state.project.scenes || []) {
    const layer = visit(scene.layers);
    if (layer) return layer;
  }
  return null;
}
export const snapshotLayer = l => ({ transform: clone(l.transform), tracks: clone(l.tracks), opacity: l.opacity });
export function restoreLayer(l, s) {
  for (const k of ['transform', 'tracks', 'opacity']) { if (s[k] === undefined) delete l[k]; else l[k] = clone(s[k]); }
}
export function animPatch(layerId, after, label = 'Edit') {
  let before;
  return {
    label,
    do() { const l = findLayer(layerId); before = snapshotLayer(l); restoreLayer(l, after); },
    undo() { restoreLayer(findLayer(layerId), before); },
  };
}
