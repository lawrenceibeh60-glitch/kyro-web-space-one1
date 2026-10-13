"""LRU cache policy with an optional entry cap."""
from collections import OrderedDict


class LRUCache:
    def __init__(self, max_entries=128):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._items = OrderedDict()

    def get(self, key, default=None):
        if key not in self._items:
            return default
        self._items.move_to_end(key)
        return self._items[key]

    def put(self, key, value):
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)

    def clear(self):
        self._items.clear()
