"""Validated indexed triangle mesh value type."""
from dataclasses import dataclass, field
from engine.math.bounding_boxes import from_points


@dataclass
class Mesh2D:
    vertices: list
    triangles: list
    attributes: dict = field(default_factory=dict)

    def __post_init__(self):
        self.vertices = [tuple(vertex[:2]) for vertex in self.vertices]
        self.triangles = [tuple(triangle) for triangle in self.triangles]
        for triangle in self.triangles:
            if len(triangle) != 3 or any(not isinstance(index, int) or not 0 <= index < len(self.vertices) for index in triangle):
                raise ValueError(f"Invalid triangle indices: {triangle}")

    @property
    def bounds(self):
        return from_points(self.vertices)

    def to_dict(self):
        return {"vertices": [list(point) for point in self.vertices],
                "triangles": [list(triangle) for triangle in self.triangles],
                "attributes": self.attributes}
