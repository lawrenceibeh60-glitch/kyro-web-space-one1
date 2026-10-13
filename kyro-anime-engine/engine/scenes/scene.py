"""Scene document wrapper with layer lookup and mutation."""
from copy import deepcopy


class Scene:
    def __init__(self, document):
        if not isinstance(document, dict) or not isinstance(document.get("id"), str):
            raise ValueError("Scene requires an object with a string id")
        self._document = deepcopy(document)
        self._document.setdefault("layers", [])

    @property
    def id(self):
        return self._document["id"]

    @property
    def layers(self):
        return self._document["layers"]

    def find_layer(self, layer_id):
        return next((layer for layer in self.layers if layer.get("id") == layer_id), None)

    def add_layer(self, layer):
        if not isinstance(layer, dict) or not isinstance(layer.get("id"), str):
            raise ValueError("Layer requires a string id")
        if self.find_layer(layer["id"]):
            raise ValueError(f"Layer already exists: {layer['id']}")
        self.layers.append(deepcopy(layer))
        return self.layers[-1]

    def to_dict(self):
        return deepcopy(self._document)
