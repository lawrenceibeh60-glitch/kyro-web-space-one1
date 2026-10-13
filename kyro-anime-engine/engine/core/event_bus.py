"""Synchronous event dispatch with deterministic subscription cleanup."""
from collections import defaultdict
from engine.core.errors import ValidationError


class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)

    def on(self, event, callback):
        if not callable(callback):
            raise ValidationError("Event listener must be callable")
        self._listeners[event].append(callback)
        return lambda: self.off(event, callback)

    def once(self, event, callback):
        def wrapper(*args, **kwargs):
            self.off(event, wrapper)
            return callback(*args, **kwargs)
        self.on(event, wrapper)
        return wrapper

    def off(self, event, callback):
        listeners = self._listeners.get(event, [])
        try:
            listeners.remove(callback)
        except ValueError:
            return False
        if not listeners:
            self._listeners.pop(event, None)
        return True

    def emit(self, event, *args, **kwargs):
        return [callback(*args, **kwargs) for callback in tuple(self._listeners.get(event, ()))]

    def clear(self, event=None):
        if event is None:
            self._listeners.clear()
        else:
            self._listeners.pop(event, None)

    def listener_count(self, event):
        return len(self._listeners.get(event, ()))
