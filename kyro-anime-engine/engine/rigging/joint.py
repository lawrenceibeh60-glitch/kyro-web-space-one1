"""Joint definitions with optional angular and positional limits."""
from dataclasses import dataclass


@dataclass
class Joint:
    id: str
    parent_id: str | None = None
    pivot: tuple = (0.0, 0.0)
    rotation: float = 0.0
    min_rotation: float = -180.0
    max_rotation: float = 180.0

    def clamp_rotation(self, value):
        if self.min_rotation > self.max_rotation:
            raise ValueError("Joint rotation limits are inverted")
        return max(self.min_rotation, min(self.max_rotation, value))
