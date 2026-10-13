"""Thread-safe bounded least-recently-used render cache."""
from collections import OrderedDict
from threading import RLock


class RenderCache:
    def __init__(self, max_items=256):
        if max_items < 1:
            raise ValueError("max_items must be positive")
        self.max_items = max_items
        self._items = OrderedDict()
        self._lock = RLock()

    def get(self, key, default=None):
        with self._lock:
            if key not in self._items:
                return default
            self._items.move_to_end(key)
            return self._items[key]

    def put(self, key, value):
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)
        return value

    def clear(self):
        with self._lock:
            self._items.clear()

    def __len__(self):
        return len(self._items)
