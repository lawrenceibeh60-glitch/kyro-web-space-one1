"""Polyline path utilities for measurement, flattening and bounding."""
from engine.math.bounding_boxes import from_points
from engine.geometry.points import polyline_length


class Path2D:
    def __init__(self, points=(), *, closed=False):
        self.points = [tuple(point[:2]) for point in points]
        self.closed = bool(closed)

    @property
    def length(self):
        result = polyline_length(self.points)
        if self.closed and len(self.points) > 2:
            result += polyline_length([self.points[-1], self.points[0]])
        return result

    @property
    def bounds(self):
        return from_points(self.points)

    def transformed(self, function):
        return Path2D((function(point) for point in self.points), closed=self.closed)

    def to_dict(self):
        return {"points": [list(point) for point in self.points], "closed": self.closed}
