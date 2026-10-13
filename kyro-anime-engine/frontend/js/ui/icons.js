// frontend/js/ui/icons.js - the only place UI icons come from (inline SVG, 24x24 grid, stroke = currentColor).
// Use <i data-icon="name"></i> in HTML (hydrate() fills it) or svg('name') in JS.
const ICONS = {
  home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
  undo: '<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 010 12h-3"/>',
  redo: '<path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 000 12h3"/>',
  save: '<path d="M5 3h11l4 4v13a1 1 0 01-1 1H5a1 1 0 01-1-1V4a1 1 0 011-1z"/><path d="M8 3v6h8V3"/><path d="M8 21v-7h8v7"/>',
  download: '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 20h16"/>',
  plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  close: '<path d="M6 6l12 12"/><path d="M18 6L6 18"/>',
  hand: '<path d="M18 11V6a2 2 0 00-2-2 2 2 0 00-2 2"/><path d="M14 10V4a2 2 0 00-2-2 2 2 0 00-2 2v2"/><path d="M10 10.5V6a2 2 0 00-2-2 2 2 0 00-2 2v8"/><path d="M18 8a2 2 0 114 0v6a8 8 0 01-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 012.83-2.82L7 15"/>',
  camera: '<path d="M3 7h4l2-3h6l2 3h4v13H3z"/><circle cx="12" cy="13" r="4"/>',
  light: '<path d="M9 18h6M10 22h4"/><path d="M8 14a6 6 0 118 0c-1 1-1.5 2-1.5 4h-5C9.5 16 9 15 8 14z"/><path d="M12 1v2M3.5 4.5L5 6M1 12h2M19 6l1.5-1.5M21 12h2"/>',
  brush: '<path d="M17 3a2.85 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5z"/><path d="M15 5l4 4"/>',
  eraser: '<path d="M7 21l-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6c1 1 1 2.5 0 3.4L13 21"/><path d="M22 21H7"/><path d="M5 11l9 9"/>',
  move: '<path d="M5 9l-3 3 3 3"/><path d="M9 5l3-3 3 3"/><path d="M15 19l-3 3-3-3"/><path d="M19 9l3 3-3 3"/><path d="M2 12h20"/><path d="M12 2v20"/>',
  rotate: '<path d="M21 12a9 9 0 11-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
  scale: '<path d="M21 3L9 15"/><path d="M12 3H3v18h18v-9"/><path d="M16 3h5v5"/><path d="M14 15H9v-5"/>',
  play: '<path d="M7 4l13 8-13 8z"/>',
  pause: '<path d="M6 4h4v16H6z"/><path d="M14 4h4v16h-4z"/>',
  first: '<path d="M19 20L9 12l10-8v16z"/><path d="M5 19V5"/>',
  last: '<path d="M5 4l10 8-10 8V4z"/><path d="M19 5v14"/>',
  prev: '<path d="M15 18l-6-6 6-6"/>',
  next: '<path d="M9 18l6-6-6-6"/>',
  loop: '<path d="M17 2l4 4-4 4"/><path d="M3 11v-1a4 4 0 014-4h14"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v1a4 4 0 01-4 4H3"/>',
  record: '<circle cx="12" cy="12" r="7"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  'eye-off': '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><path d="M3 3l18 18"/>',
  lock: '<path d="M5 11h14v10H5z"/><path d="M8 11V7a4 4 0 018 0v4"/>',
  unlock: '<path d="M5 11h14v10H5z"/><path d="M8 11V7a4 4 0 017.5-2"/>',
  diamond: '<path d="M12 3l9 9-9 9-9-9z"/>',
  'diamond-fill': '<path d="M12 3l9 9-9 9-9-9z"/>',
  dot: '<circle cx="12" cy="12" r="6"/>',
  sliders: '<path d="M4 6h8M18 6h2M4 12h2M12 12h8M4 18h10M20 18h0"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
  object: '<path d="M12 2l9 5v10l-9 5-9-5V7z"/><path d="M12 12l9-5"/><path d="M12 12v10"/><path d="M12 12L3 7"/>',
  film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
  'chevron-down': '<path d="M6 9l6 6 6-6"/>',
  outliner: '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
  timeline: '<path d="M3 6h18M3 12h18M3 18h18"/><path d="M8 4v4M15 10v4M11 16v4"/>',
  history: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  asset: '<path d="M4 5h16v14H4z"/><path d="M8 15l3-3 2 2 2-3 3 4"/><circle cx="9" cy="9" r="1"/>',
  line: '<path d="M5 19L19 5"/>',
  rectangle: '<rect x="4" y="5" width="16" height="14" rx="1"/>',
  ellipse: '<ellipse cx="12" cy="12" rx="9" ry="6"/>',
  polygon: '<path d="M7 3h10l6 9-6 9H7l-6-9z"/>',
  star: '<path d="M12 2l2.9 6.2 6.8.9-5 4.8 1.2 6.8-5.9-3.3-5.9 3.3 1.2-6.8-5-4.8 6.8-.9z"/>',
  fill: '<path d="M4 14l8-10 8 10-8 6z"/><path d="M4 14h16"/>',
  eyedropper: '<path d="M14 5l5 5"/><path d="M12 7L4 15v5h5l8-8"/><path d="M16 3l5 5"/>',
  nodes: '<circle cx="5" cy="19" r="2"/><circle cx="12" cy="6" r="2"/><circle cx="19" cy="15" r="2"/><path d="M6.5 17.5l4-9M13.8 7.2l4 6"/>',
  check: '<path d="M5 12l5 5 9-10"/>',
  reset: '<path d="M3 12a9 9 0 109-9c-2.52 0-4.93 1-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  duplicate: '<rect x="8" y="8" width="12" height="12" rx="1"/><path d="M16 8V5a1 1 0 00-1-1H5a1 1 0 00-1 1v10a1 1 0 001 1h3"/>',
  'select-all': '<rect x="4" y="4" width="16" height="16" rx="1" stroke-dasharray="3 3"/>',
  wave: '<path d="M3 12c3-6 6 6 9 0s6 6 9 0"/>',
};
const FILLED = new Set(['play', 'pause', 'record', 'diamond-fill', 'dot']);

export function svg(name, cls = '') {
  const body = ICONS[name];
  if (!body) return '';
  return `<svg class="ic${FILLED.has(name) ? ' f' : ''}${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
}

export function setIcon(el, name) {
  if (el.dataset.ic === name) return; // skip needless DOM work (called every frame during playback)
  el.dataset.ic = name;
  el.innerHTML = svg(name);
}

export function hydrate(root = document) {
  root.querySelectorAll('[data-icon]').forEach(el => setIcon(el, el.dataset.icon));
}

export const iconNames = () => Object.keys(ICONS);
