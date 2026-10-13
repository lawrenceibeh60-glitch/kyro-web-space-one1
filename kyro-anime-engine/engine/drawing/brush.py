"""Brush sampling with distance-based interpolation."""
import math
from engine.drawing.pressure import normalize_pressure


class Brush:
    def __init__(self, color="#111111", width=3.0, spacing=0.25):
        if width <= 0 or spacing <= 0:
            raise ValueError("Brush width and spacing must be positive")
        self.color, self.width, self.spacing = color, float(width), float(spacing)
        self._last = None

    def begin(self, x, y, pressure=1):
        self._last = (float(x), float(y), normalize_pressure(pressure))
        return [self._last]

    def sample(self, x, y, pressure=1):
        point = (float(x), float(y), normalize_pressure(pressure))
        if self._last is None:
            return self.begin(*point)
        dx, dy = point[0] - self._last[0], point[1] - self._last[1]
        distance = math.hypot(dx, dy)
        step = max(self.width * self.spacing, 0.5)
        count = max(1, math.ceil(distance / step))
        points = [
            tuple(self._last[axis] + (point[axis] - self._last[axis]) * index / count for axis in range(3))
            for index in range(1, count + 1)
        ]
        self._last = point
        return points

    def end(self):
        self._last = None
