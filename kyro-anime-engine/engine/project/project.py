"""Mutable project document wrapper with non-destructive accessors."""
from copy import deepcopy
from engine.data.normalizer import normalize_project


class Project:
    def __init__(self, document):
        self._document = normalize_project(document)

    @property
    def id(self):
        return self._document.get("id")

    @property
    def name(self):
        return self._document["name"]

    @property
    def settings(self):
        return self._document["settings"]

    @property
    def document(self):
        return deepcopy(self._document)

    def scene(self, scene_id):
        return next((scene for scene in self._document["scenes"] if scene.get("id") == scene_id), None)

    def drawing(self, drawing_id):
        return self._document["drawings"].get(drawing_id)

    def to_dict(self):
        return self.document

    def replace(self, document):
        self._document = normalize_project(document)
        return self
