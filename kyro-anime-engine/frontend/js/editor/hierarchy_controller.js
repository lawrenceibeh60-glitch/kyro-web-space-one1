// Recursive scene outliner: paint-order rows, nested groups, visibility/lock controls and drag reparenting.
import { svg } from '../ui/icons.js';

export function renderLayerHierarchy(container, layers, {
  selectedId = null,
  onSelect = () => {},
  onRename = () => {},
  onToggleVisibility = () => {},
  onToggleLock = () => {},
  onReparent = () => {},
  onError = () => {},
} = {}) {
  if (!container) return;
  container.replaceChildren();
  const renderNodes = (nodes, parent, depth = 0) => {
    for (const layer of [...(Array.isArray(nodes) ? nodes : [])].reverse()) {
      if (!layer) continue;
      const item = document.createElement('li');
      item.className = 'layer' + (layer.id === selectedId ? ' active' : '') + (layer.type === 'group' ? ' layer-group' : '');
      item.dataset.layerId = layer.id;
      item.draggable = true;
      item.style.paddingLeft = (depth * 12) + 'px';
      item.ondragstart = event => {
        event.dataTransfer?.setData('text/kae-layer-id', layer.id);
        if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
      };
      item.ondragover = event => {
        if (layer.type === 'group' || layer.type === 'character_instance') {
          event.preventDefault();
          if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
        }
      };
      item.ondrop = event => {
        event.preventDefault(); event.stopPropagation();
        const sourceId = event.dataTransfer?.getData('text/kae-layer-id');
        if (!sourceId || sourceId === layer.id) return;
        try { onReparent(sourceId, layer.id); } catch (error) { onError(error); }
      };
      const visibility = document.createElement('button');
      visibility.type = 'button';
      visibility.innerHTML = svg(layer.visible === false ? 'eye-off' : 'eye');
      visibility.title = layer.visible === false ? 'Show layer' : 'Hide layer';
      visibility.setAttribute('aria-label', visibility.title);
      visibility.onclick = event => { event.stopPropagation(); onToggleVisibility(layer.id, layer.visible === false); };
      const lock = document.createElement('button');
      lock.type = 'button';
      lock.innerHTML = svg(layer.locked ? 'lock' : 'unlock');
      lock.title = layer.locked ? 'Unlock layer' : 'Lock layer';
      lock.setAttribute('aria-label', lock.title);
      lock.onclick = event => { event.stopPropagation(); onToggleLock(layer.id, !layer.locked); };
      const name = document.createElement('span');
      name.className = 'nm';
      name.textContent = (layer.type === 'group' ? '▾ ' : '') + (layer.name || layer.id);
      name.title = 'Double-click to rename';
      item.append(visibility, lock, name);
      item.onclick = event => { event.stopPropagation(); onSelect(layer.id); };
      item.ondblclick = event => { event.preventDefault(); event.stopPropagation(); onRename(layer.id); };
      parent.append(item);
      if (Array.isArray(layer.children) && layer.children.length) {
        const children = document.createElement('ul');
        children.className = 'layers layer-children';
        item.append(children);
        renderNodes(layer.children, children, depth + 1);
      }
    }
  };
  container.ondragover = event => event.preventDefault();
  container.ondrop = event => {
    if (event.target.closest('.layer')) return;
    event.preventDefault();
    const sourceId = event.dataTransfer?.getData('text/kae-layer-id');
    if (!sourceId) return;
    try { onReparent(sourceId, null); } catch (error) { onError(error); }
  };
  renderNodes(layers, container);
}
