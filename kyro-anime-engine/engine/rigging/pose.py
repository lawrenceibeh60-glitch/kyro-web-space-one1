"""Named rig pose value and serialization helpers."""
from copy import deepcopy


class Pose:
    def __init__(self, bones=None, name="Pose"):
        self.name = name
        self.bones = deepcopy(bones or {})

    def set_rotation(self, bone_id, degrees):
        self.bones.setdefault(bone_id, {})["rotation"] = float(degrees)

    def rotation(self, bone_id, default=0):
        return self.bones.get(bone_id, {}).get("rotation", default)

    def to_dict(self):
        return {"name": self.name, "bones": deepcopy(self.bones)}
