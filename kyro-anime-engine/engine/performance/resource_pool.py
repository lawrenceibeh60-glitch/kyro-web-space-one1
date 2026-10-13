"""Bounded reusable resource pool."""
from collections import deque


class ResourcePool:
    def __init__(self, factory, max_size=16, disposer=None):
        if max_size < 1:
            raise ValueError("max_size must be positive")
        self.factory, self.max_size = factory, max_size
        self.disposer = disposer or (lambda resource: None)
        self._available = deque()

    def acquire(self):
        return self._available.pop() if self._available else self.factory()

    def release(self, resource):
        if len(self._available) < self.max_size:
            self._available.append(resource)
        else:
            self.disposer(resource)

    def clear(self):
        while self._available:
            self.disposer(self._available.pop())
