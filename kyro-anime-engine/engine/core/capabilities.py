"""Capability discovery for optional engine features."""
from engine.core.registry import Registry


class Capabilities:
    def __init__(self):
        self._features = Registry()

    def provide(self, name, provider=True):
        return self._features.register(name, provider, replace=True)

    def remove(self, name):
        if name in self._features:
            return self._features.unregister(name)
        return None

    def supports(self, name):
        return name in self._features and bool(self._features.get(name))

    def get(self, name, default=None):
        return self._features.get(name, default)

    def list(self):
        return tuple(name for name in self._features.names() if self.supports(name))
