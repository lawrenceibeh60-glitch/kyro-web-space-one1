// frontend/js/editor/workspace_layout.js - Blender-style workspaces and area editor-type switching.
// Three areas (A, B = right column / under the viewport, C = bottom). Each shows one editor panel.
// Panels are real DOM nodes that get moved between areas, so every editor keeps its state and listeners.
import { bus } from '../core/event_bus.js';
import { svg } from '../ui/icons.js';

export const EDITORS = {
  outliner: { label: 'Outliner', icon: 'outliner' },
  properties: { label: 'Properties', icon: 'sliders' },
  timeline: { label: 'Timeline', icon: 'timeline' },
  graph: { label: 'Graph Editor', icon: 'timeline' },
  geometry: { label: 'Geometry Nodes', icon: 'nodes' },
  history: { label: 'History', icon: 'history' },
  assets: { label: 'Asset Browser', icon: 'asset' },
  studio: { label: 'Studio Tools', icon: 'sliders' },
};

export const WORKSPACES = {
  draw: { label: 'Layout', tool: 'brush', tab: 'tool', bottom: 'clamp(210px, 30vh, 320px)', slots: { A: 'outliner', B: 'properties', C: 'timeline' } },
  animate: { label: '2D Animation', tool: 'brush', tab: 'tool', bottom: 'clamp(230px, 32vh, 350px)', slots: { A: 'outliner', B: 'properties', C: 'timeline' } },
  edit: { label: 'Rigging', tool: 'edit', tab: 'tool', bottom: 'clamp(180px, 28vh, 300px)', slots: { A: 'outliner', B: 'properties', C: 'timeline' } },
  studio: { label: 'Studio', tool: 'move', tab: 'object', bottom: 'clamp(190px, 30vh, 300px)', slots: { A: 'outliner', B: 'studio', C: 'timeline' } },
  nodes: { label: 'Geometry Nodes', tool: 'move', tab: 'object', bottom: 'clamp(180px, 28vh, 300px)', slots: { A: 'geometry', B: 'outliner', C: 'timeline' } },
};

const KEY = 'kae.layout';
const SLOTS = ['A', 'B', 'C'];

// Put `editor` into `slot`. If another area already shows it, the two areas swap; otherwise the old editor is parked.
export function assignEditor(slots, slot, editor) {
  const next = { ...slots };
  const other = SLOTS.find(s => s !== slot && next[s] === editor);
  if (other) next[other] = next[slot];
  next[slot] = editor;
  return next;
}

export function sanitizeSlots(slots, fallback) {
  if (!slots) return { ...fallback };
  const seen = new Set();
  for (const s of SLOTS) {
    if (!EDITORS[slots[s]] || seen.has(slots[s])) return { ...fallback };
    seen.add(slots[s]);
  }
  return { A: slots.A, B: slots.B, C: slots.C };
}

function load() { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (_) { return {}; } }
function persist(d) { try { localStorage.setItem(KEY, JSON.stringify(d)); } catch (_) { /* ignore */ } }

export function initWorkspaceLayout({ onTool, onTab }) {
  const $ = id => document.getElementById(id);
  const saved = load(), custom = saved.slots || {};
  const savedWorkspace = saved.current === 'draw' ? 'animate' : saved.current;
  let current = WORKSPACES[savedWorkspace] ? savedWorkspace : 'animate';
  let slots = sanitizeSlots(custom[current], WORKSPACES[current].slots);
  const heads = {};
  let menu = null;

  const save = () => {
    custom[current] = slots;
    persist({ ...saved, current, slots: custom });
  };

  const app = document.querySelector('.app');
  const focusButton = $('canvasFocus');
  focusButton?.addEventListener('click', () => {
    const focused = app.classList.toggle('canvas-focus');
    focusButton.setAttribute('aria-pressed', String(focused));
    focusButton.textContent = focused ? 'Restore Panels' : 'Focus Canvas';
    bus.emit('layout');
  });
  window.addEventListener('keydown', event => {
    if (event.key === 'Escape' && app.classList.contains('canvas-focus')) {
      app.classList.remove('canvas-focus');
      focusButton?.setAttribute('aria-pressed', 'false');
      if (focusButton) focusButton.textContent = 'Focus Canvas';
      bus.emit('layout');
    }
  });

  function mount() {
    for (const ed of Object.keys(EDITORS)) $('panelPool').append($('p-' + ed));
    for (const s of SLOTS) {
      $('slot' + s).append($('p-' + slots[s]));
      const e = EDITORS[slots[s]];
      heads[s].innerHTML = `${svg(e.icon)}<span>${e.label}</span>${svg('chevron-down')}`;
    }
  }

  function closeMenu() { if (menu) { menu.remove(); menu = null; } }

  function openMenu(slot, btn) {
    closeMenu();
    menu = document.createElement('div');
    menu.className = 'menu';
    for (const [id, e] of Object.entries(EDITORS)) {
      const b = document.createElement('button');
      const on = slots[slot] === id;
      b.className = 'menu-item' + (on ? ' on' : '');
      b.innerHTML = svg(e.icon) + `<span>${e.label}</span>` + (on ? svg('check') : '');
      b.onclick = () => { slots = assignEditor(slots, slot, id); save(); mount(); closeMenu(); bus.emit('layout'); };
      menu.append(b);
    }
    document.body.append(menu);
    const r = btn.getBoundingClientRect();
    menu.style.left = Math.max(4, Math.min(r.left, window.innerWidth - 176)) + 'px';
    menu.style.top = (r.bottom + 2) + 'px';
  }

  for (const s of SLOTS) {
    const head = document.createElement('div');
    head.className = 'area-h';
    const b = document.createElement('button');
    b.className = 'area-btn'; b.title = 'Change editor type';
    b.onclick = () => openMenu(s, b);
    head.append(b);
    $('slot' + s).prepend(head);
    heads[s] = b;
  }
  document.addEventListener('pointerdown', e => { if (menu && !menu.contains(e.target) && !e.target.closest('.area-btn')) closeMenu(); });

  function highlight() {
    document.querySelectorAll('#wtabs button').forEach(b => b.classList.toggle('on', b.dataset.ws === current));
    document.documentElement.style.setProperty('--slotC-h', WORKSPACES[current].bottom);
  }

  function apply(id, { silent = false } = {}) {
    if (!WORKSPACES[id]) return;
    current = id;
    slots = sanitizeSlots(custom[id], WORKSPACES[id].slots);
    highlight(); mount(); save();
    if (!silent) { onTool(WORKSPACES[id].tool); onTab(WORKSPACES[id].tab); }
    bus.emit('layout');
  }

  document.querySelectorAll('#wtabs button').forEach(b => { b.onclick = () => apply(b.dataset.ws); });

  function resetLayout() {
    for (const k of Object.keys(custom)) delete custom[k];
    document.documentElement.style.removeProperty('--right');
    document.documentElement.style.removeProperty('--slotC-h');
    app.classList.remove('canvas-focus');
    focusButton?.setAttribute('aria-pressed', 'false');
    if (focusButton) focusButton.textContent = 'Focus Canvas';
    slots = { ...WORKSPACES[current].slots };
    highlight(); mount(); save(); bus.emit('layout');
  }

  highlight(); mount();
  return { apply, resetLayout, current: () => current, slots: () => ({ ...slots }) };
}
