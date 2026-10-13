// frontend/js/core/event_bus.js
export class EventBus {
  constructor() { this.map = new Map(); }
  on(evt, fn) {
    if (!this.map.has(evt)) this.map.set(evt, new Set());
    this.map.get(evt).add(fn);
    return () => this.off(evt, fn);
  }
  off(evt, fn) { this.map.get(evt)?.delete(fn); }
  emit(evt, data) { for (const fn of [...(this.map.get(evt) || [])]) fn(data); }
}
export const bus = new EventBus();
