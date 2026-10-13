"""Validated parented bone collection."""
from engine.core.errors import ValidationError


class Skeleton:
    def __init__(self, bones=()):
        self.bones = [bone.to_dict() if hasattr(bone, "to_dict") else dict(bone) for bone in bones]
        self.validate()

    def validate(self):
        by_id = {bone.get("id"): bone for bone in self.bones}
        if len(by_id) != len(self.bones) or None in by_id:
            raise ValidationError("Bone IDs must be present and unique")
        for bone in self.bones:
            parent = bone.get("parent_id")
            if parent is not None and parent not in by_id:
                raise ValidationError(f"Bone parent not found: {parent}")
            if parent == bone.get("id"):
                raise ValidationError(f"Bone cannot parent itself: {parent}")
            seen, current = set(), bone.get("id")
            while current is not None:
                if current in seen:
                    raise ValidationError(f"Bone hierarchy cycle at {current}")
                seen.add(current)
                current = by_id[current].get("parent_id")
        return True

    def get(self, bone_id):
        return next((bone for bone in self.bones if bone.get("id") == bone_id), None)

    def roots(self):
        return [bone for bone in self.bones if bone.get("parent_id") is None]
