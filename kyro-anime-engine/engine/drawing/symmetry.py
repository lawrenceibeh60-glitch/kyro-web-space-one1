"""Reflect or rotate point samples around a drawing axis."""
import math


def reflect_point(point, *, axis="vertical", center=(0, 0)):
    x, y = point[:2]
    cx, cy = center
    if axis == "vertical":
        return (2 * cx - x, y)
    if axis == "horizontal":
        return (x, 2 * cy - y)
    if axis == "both":
        return (2 * cx - x, 2 * cy - y)
    raise ValueError("axis must be vertical, horizontal, or both")


def mirror_stroke(stroke, *, axis="vertical", center=(0, 0)):
    mirrored = dict(stroke)
    mirrored["points"] = [
        [*reflect_point(point, axis=axis, center=center), *point[2:]]
        for point in stroke.get("points", [])
    ]
    return mirrored


def radial_points(point, count, *, center=(0, 0)):
    if count < 1:
        raise ValueError("count must be positive")
    angle_step = math.tau / count
    x, y = point[0] - center[0], point[1] - center[1]
    return [
        (center[0] + x * math.cos(angle_step * i) - y * math.sin(angle_step * i),
         center[1] + x * math.sin(angle_step * i) + y * math.cos(angle_step * i))
        for i in range(count)
    ]
