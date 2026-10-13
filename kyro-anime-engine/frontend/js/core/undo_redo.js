// frontend/js/core/undo_redo.js
import { bus } from './event_bus.js';

export class UndoStack {
  constructor(limit = 200) { this.limit = limit; this.undoS = []; this.redoS = []; }
  push(cmd) {
    this.undoS.push(cmd);
    if (this.undoS.length > this.limit) this.undoS.shift();
    this.redoS.length = 0;
    bus.emit('history');
  }
  undo() { const c = this.undoS.pop(); if (c) { this.redoS.push(c); bus.emit('history'); } return c || null; }
  redo() { const c = this.redoS.pop(); if (c) { this.undoS.push(c); bus.emit('history'); } return c || null; }
  clear() { this.undoS.length = 0; this.redoS.length = 0; bus.emit('history'); }
  get canUndo() { return this.undoS.length > 0; }
  get canRedo() { return this.redoS.length > 0; }
}
export const history = new UndoStack();
