"""In-memory pose library with safe copying and name-based lookup."""
from copy import deepcopy


class PoseLibrary:
    def __init__(self, poses=None):
        self._poses = {}
        for pose in poses or []:
            self.save(pose["name"], pose)

    def save(self, name, pose):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Pose name must not be empty")
        self._poses[name] = deepcopy(pose)
        return deepcopy(self._poses[name])

    def get(self, name):
        return deepcopy(self._poses.get(name))

    def delete(self, name):
        return self._poses.pop(name, None) is not None

    def names(self):
        return tuple(self._poses)
