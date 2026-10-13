"""Rotation, distance, and pin constraints for 2D skeletons."""
import math


def clamp_rotation(angle, minimum=-180, maximum=180):
    if minimum > maximum:
        raise ValueError("minimum rotation must not exceed maximum")
    return max(minimum, min(maximum, angle))


def constrain_distance(point, origin, minimum=0, maximum=float("inf")):
    if minimum < 0 or maximum < minimum:
        raise ValueError("Invalid distance limits")
    dx, dy = point[0] - origin[0], point[1] - origin[1]
    length = math.hypot(dx, dy)
    target = max(minimum, min(maximum, length))
    if length == 0:
        return (origin[0] + target, origin[1])
    return (origin[0] + dx * target / length, origin[1] + dy * target / length)


def pin(point, target, weight=1.0):
    weight = max(0.0, min(1.0, weight))
    return (point[0] + (target[0] - point[0]) * weight,
            point[1] + (target[1] - point[1]) * weight)
