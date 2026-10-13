"""Build vector stroke payloads from pointer samples."""
from engine.core.identifiers import new_id
from engine.drawing.smoothing import moving_average


class PathBuilder:
    def __init__(self, *, color="#111111", width=3, tool="brush", smoothing=0):
        self.color, self.width, self.tool = color, width, tool
        self.smoothing = max(0, int(smoothing))
        self.points = []

    def add(self, x, y, pressure=1):
        point = (float(x), float(y), max(0.0, min(1.0, float(pressure))))
        if not self.points or point != self.points[-1]:
            self.points.append(point)
        return point

    def finish(self, *, fill=None, closed=False):
        points = moving_average(self.points, self.smoothing) if self.smoothing else list(self.points)
        if not points:
            return None
        stroke = {"id": new_id("stroke"), "tool": self.tool, "color": self.color,
                  "width": self.width, "points": [list(point) for point in points]}
        if fill is not None:
            stroke["fill"] = fill
        if closed:
            stroke["closed"] = True
        self.points = []
        return stroke
