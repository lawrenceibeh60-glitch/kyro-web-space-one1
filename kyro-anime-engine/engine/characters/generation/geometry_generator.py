"""Generate simple closed polygon geometry from landmark sets."""
import math


def ellipse(center, width, height, segments=24):
    if width <= 0 or height <= 0 or segments < 3:
        raise ValueError("Ellipse dimensions must be positive and segments >= 3")
    return [(center[0] + width / 2 * math.cos(2 * math.pi * i / segments),
             center[1] + height / 2 * math.sin(2 * math.pi * i / segments))
            for i in range(segments)]


def mirror_points(points, axis_x=0):
    return [(2 * axis_x - point[0], point[1]) for point in points]
