// frontend/js/ui/history_panel.js - undo history list; tap an entry to jump to that state.
import { bus } from '../core/event_bus.js';
import { history } from '../core/undo_redo.js';
import { undo, redo } from '../core/command_manager.js';

export function historyItems() {
  const items = [{ label: 'Original', kind: 'past', idx: -1, current: history.undoS.length === 0 }];
  history.undoS.forEach((c, i) => items.push({ label: c.label || 'Edit', kind: 'past', idx: i, current: i === history.undoS.length - 1 }));
  [...history.redoS].reverse().forEach((c, j) => items.push({ label: c.label || 'Edit', kind: 'future', idx: j, current: false }));
  return items;
}

export function jumpTo(item) {
  if (item.kind === 'past') { let n = history.undoS.length - 1 - item.idx; while (n-- > 0) undo(); }
  else { let n = item.idx + 1; while (n-- > 0) redo(); }
}

export function initHistoryPanel() {
  const ul = document.getElementById('histList');
  function render() {
    ul.innerHTML = '';
    const items = historyItems();
    for (const it of items.slice(-150)) {
      const li = document.createElement('li');
      li.className = 'layer' + (it.current ? ' active' : '') + (it.kind === 'future' ? ' future' : '');
      const span = document.createElement('span');
      span.className = 'nm'; span.textContent = it.label;
      li.append(span);
      li.onclick = () => jumpTo(it);
      ul.append(li);
      if (it.current) requestAnimationFrame(() => li.scrollIntoView({ block: 'nearest' }));
    }
  }
  bus.on('history', render);
  render();
  return { render };
}
