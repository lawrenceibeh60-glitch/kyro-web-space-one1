"""Drawing document container with simple hit-testing and serialization."""
from dataclasses import dataclass, field
from engine.core.identifiers import new_id
from engine.math.bounding_boxes import from_points
from engine.math.intersections import point_on_segment


@dataclass
class Drawing:
    name: str = "Drawing"
    strokes: list = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("drawing"))

    @property
    def bounds(self):
        points = [point[:2] for stroke in self.strokes for point in stroke.get("points", [])]
        return from_points(points)

    def add_stroke(self, stroke):
        self.strokes.append(stroke.to_dict() if hasattr(stroke, "to_dict") else dict(stroke))
        return self.strokes[-1]

    def remove_stroke(self, stroke_id):
        before = len(self.strokes)
        self.strokes = [stroke for stroke in self.strokes if stroke.get("id") != stroke_id]
        return len(self.strokes) != before

    def to_dict(self):
        return {"id": self.id, "name": self.name, "strokes": self.strokes}
