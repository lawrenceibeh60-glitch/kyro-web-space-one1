"""Portable render command independent of a specific raster backend."""
from dataclasses import dataclass, field


@dataclass
class DrawCommand:
    kind: str
    points: list
    color: str = "#111111"
    width: float = 1.0
    fill: str | None = None
    opacity: float = 1.0
    z: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "kind": self.kind, "points": [list(point) for point in self.points],
            "color": self.color, "width": self.width, "fill": self.fill,
            "opacity": self.opacity, "z": self.z, "metadata": dict(self.metadata),
        }
