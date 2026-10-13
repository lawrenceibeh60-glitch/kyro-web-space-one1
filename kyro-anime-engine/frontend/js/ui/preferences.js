// frontend/js/ui/preferences.js - user preferences (kept in this browser), keymap list, auto-save timer.
import { state } from '../core/state_manager.js';

const KEY = 'kae.prefs';
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

export const prefs = { fontSize: 13, handle: 6, autosave: false };
try { Object.assign(prefs, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (_) { /* no storage: defaults */ }
prefs.fontSize = clamp(+prefs.fontSize || 13, 11, 18);
prefs.handle = clamp(+prefs.handle || 6, 4, 14);
prefs.autosave = !!prefs.autosave;

export const KEYMAP = [
  ['Space', 'Play / pause'], ['Left / Right', 'Previous / next frame'], ['Up / Down', 'Next / previous key'], ['Home / End', 'First / last frame'],
  ['B', 'Brush'], ['E', 'Eraser'], ['G', 'Grease Pencil'], ['H', 'Hand'], ['L', 'Line'], ['U', 'Rectangle'], ['O', 'Ellipse'], ['F', 'Fill'], ['C', 'Eyedropper'], ['M', 'Move layer'], ['R', 'Rotate layer'], ['S', 'Scale layer'],
  ['Tab', 'Toggle Edit mode'], ['A', 'Select all points (Edit)'], ['X', 'Delete key / points'],
  ['F2', 'Rename selected layer'], ['Shift+D', 'Duplicate selected layer'],
  ['I', 'Insert keys'], ['Alt+I', 'Delete keys'], ['[  ]', 'Brush size'], ['0', 'Fit view'], ['+  -', 'Zoom'],
  ['Ctrl+Z', 'Undo'], ['Ctrl+Shift+Z', 'Redo'], ['Ctrl+S', 'Save'], ['Ctrl+E', 'Export'],
];

export function savePrefs() { try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch (_) { /* ignore */ } }
export function applyPrefs() { document.documentElement.style.setProperty('--fs', prefs.fontSize + 'px'); }

export function initPreferences({ save, resetLayout }) {
  const $ = id => document.getElementById(id);
  const sync = () => {
    $('p_font').value = prefs.fontSize; $('p_fontV').textContent = prefs.fontSize + 'px';
    $('p_handle').value = prefs.handle; $('p_handleV').textContent = prefs.handle;
    $('p_autosave').checked = prefs.autosave;
  };
  $('p_font').oninput = e => { prefs.fontSize = +e.target.value; applyPrefs(); savePrefs(); sync(); };
  $('p_handle').oninput = e => { prefs.handle = +e.target.value; savePrefs(); sync(); };
  $('p_autosave').onchange = e => { prefs.autosave = e.target.checked; savePrefs(); };
  $('p_reset').onclick = resetLayout;
  const km = $('keymap');
  km.innerHTML = '';
  for (const [k, what] of KEYMAP) {
    const a = document.createElement('kbd'); a.textContent = k;
    const b = document.createElement('span'); b.textContent = what;
    km.append(a, b);
  }
  setInterval(() => { if (prefs.autosave && state.dirty && state.project) save({ silent: true }); }, 20000);
  applyPrefs(); sync();
}
