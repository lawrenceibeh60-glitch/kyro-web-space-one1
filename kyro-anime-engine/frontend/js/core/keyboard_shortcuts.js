// frontend/js/core/keyboard_shortcuts.js - Blender-style keys
export function initShortcuts(a) {
  window.addEventListener('keydown', e => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
    const k = e.key.toLowerCase(), mod = e.ctrlKey || e.metaKey;
    if (mod && k === 'z') { e.preventDefault(); e.shiftKey ? a.redo() : a.undo(); }
    else if (mod && k === 'y') { e.preventDefault(); a.redo(); }
    else if (mod && k === 's') { e.preventDefault(); a.save(); }
    else if (mod && k === 'e') { e.preventDefault(); a.exp(); }
    else if (mod) return;
    else if (e.code === 'Space') { e.preventDefault(); a.play(); }
    else if (k === 'arrowright') a.step(1);
    else if (k === 'arrowleft') a.step(-1);
    else if (k === 'arrowup') { e.preventDefault(); a.jump(1); }
    else if (k === 'arrowdown') { e.preventDefault(); a.jump(-1); }
    else if (k === 'home') a.first();
    else if (k === 'end') a.last();
    else if (k === 'i') e.altKey ? a.unkey() : a.key();
    else if (e.key === 'F2') { e.preventDefault(); a.renameLayer(); }
    else if (e.shiftKey && k === 'd') { e.preventDefault(); a.duplicateLayer(); }
    else if (k === 'x' || k === 'delete') a.delKey();
    else if (k === 'tab') { e.preventDefault(); a.toggleEdit(); }
    else if (k === 'a') a.selectAll();
    else if (e.shiftKey && k === 'f') a.toggleCanvasFocus();
    else if (k === '0') a.fit();
    else if (k === '=' || k === '+') a.zoom(1.25);
    else if (k === '-') a.zoom(0.8);
    else if (k === 'b') a.tool('brush');
    else if (k === 'e') a.tool('eraser');
    else if (k === 'g') a.tool('grease');
    else if (k === 'l') a.tool('line');
    else if (k === 'u') a.tool('rectangle');
    else if (k === 'o') a.tool('ellipse');
    else if (k === 'p') a.tool('polygon');
    else if (k === 't') a.tool('star');
    else if (k === 'f') a.tool('fill');
    else if (k === 'c') a.tool('eyedropper');
    else if (k === 'h') a.tool('pan');
    else if (k === 'k') a.tool('camera');
    else if (k === 'm') a.tool('move');
    else if (k === 'r') a.tool('rotate');
    else if (k === 's') a.tool('scale');
    else if (k === '[') a.size(-1);
    else if (k === ']') a.size(1);
  });
}
