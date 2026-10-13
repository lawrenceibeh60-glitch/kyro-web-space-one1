"""Small typed registry for engine services, renderers and plugins."""
from engine.core.errors import MissingResourceError, ValidationError


class Registry:
    def __init__(self):
        self._items = {}

    def register(self, name, value, *, replace=False):
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Registry name must be a non-empty string")
        if name in self._items and not replace:
            raise ValidationError(f"Registry entry already exists: {name}")
        self._items[name] = value
        return value

    def unregister(self, name):
        try:
            return self._items.pop(name)
        except KeyError as error:
            raise MissingResourceError(name) from error

    def get(self, name, default=None):
        return self._items.get(name, default)

    def require(self, name):
        try:
            return self._items[name]
        except KeyError as error:
            raise MissingResourceError(name) from error

    def create(self, name, *args, **kwargs):
        factory = self.require(name)
        if not callable(factory):
            raise ValidationError(f"Registry entry is not callable: {name}")
        return factory(*args, **kwargs)

    def names(self):
        return tuple(self._items)

    def __contains__(self, name):
        return name in self._items

    def __len__(self):
        return len(self._items)
