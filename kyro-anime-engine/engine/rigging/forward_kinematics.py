"""Resolve world-space bone pivot and rotation from parented local bones."""
import math
from engine.rigging.skeleton import Skeleton


def evaluate(skeleton, pose=None):
    bones = skeleton.bones if isinstance(skeleton, Skeleton) else Skeleton(skeleton).bones
    by_id = {bone["id"]: bone for bone in bones}
    pose = pose or {}
    result = {}

    def solve(bone_id):
        if bone_id in result:
            return result[bone_id]
        bone = by_id[bone_id]
        local = pose.get(bone_id, {})
        pivot = bone.get("pivot", {})
        x, y = pivot.get("x", 0), pivot.get("y", 0)
        rotation = bone.get("rotation", 0) + local.get("rotation", 0)
        parent_id = bone.get("parent_id")
        if parent_id is not None:
            parent = solve(parent_id)
            angle = math.radians(parent["rotation"])
            x, y = x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)
            x += parent["x"]
            y += parent["y"]
            rotation += parent["rotation"]
        result[bone_id] = {"x": x, "y": y, "rotation": rotation}
        return result[bone_id]

    for bone in bones:
        solve(bone["id"])
    return result
