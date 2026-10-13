"""Editable vector stroke representation and validation."""
from dataclasses import dataclass, field
from engine.core.identifiers import new_id
from engine.core.errors import ValidationError


@dataclass
class Stroke:
    points: list
    color: str = "#111111"
    width: float = 3.0
    tool: str = "brush"
    fill: str | None = None
    closed: bool = False
    id: str = field(default_factory=lambda: new_id("stroke"))

    def __post_init__(self):
        if not isinstance(self.points, list) or not self.points:
            raise ValidationError("Stroke points must be a non-empty list")
        normalized = []
        for point in self.points:
            if not isinstance(point, (list, tuple)) or len(point) not in (2, 3):
                raise ValidationError("Each stroke point must be [x, y, pressure?]")
            x, y = float(point[0]), float(point[1])
            pressure = float(point[2]) if len(point) == 3 else 1.0
            if not all(map(__import__("math").isfinite, (x, y, pressure))):
                raise ValidationError("Stroke coordinates and pressure must be finite")
            normalized.append((x, y, pressure))
        self.points = normalized
        if self.width <= 0:
            raise ValidationError("Stroke width must be positive")

    def to_dict(self):
        result = {
            "id": self.id, "tool": self.tool, "color": self.color,
            "width": self.width, "points": [list(point) for point in self.points],
        }
        if self.fill is not None:
            result["fill"] = self.fill
        if self.closed:
            result["closed"] = True
        return result
