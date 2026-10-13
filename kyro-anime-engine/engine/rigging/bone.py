"""Bone data model compatible with the KAE rig schema."""
from dataclasses import dataclass, field


@dataclass
class Bone:
    id: str
    name: str
    character_part_id: str
    pivot: dict
    parent_id: str | None = None
    rotation: float = 0.0
    tracks: dict = field(default_factory=dict)

    def to_dict(self):
        result = {
            "id": self.id, "name": self.name, "character_part_id": self.character_part_id,
            "pivot": dict(self.pivot), "rotation": self.rotation,
        }
        if self.parent_id is not None:
            result["parent_id"] = self.parent_id
        if self.tracks:
            result["tracks"] = self.tracks
        return result
