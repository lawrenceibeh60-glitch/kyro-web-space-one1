// frontend/js/core/selection_manager.js
import { bus } from './event_bus.js';
import { setState } from './state_manager.js';

export function selectLayer(id) {
  setState({ layerId: id });
  bus.emit('selection', { layerId: id });
}
