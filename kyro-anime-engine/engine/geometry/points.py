"""Point normalization and polyline measurements."""
from engine.math.vectors import distance, lerp


def point(value):
    if not isinstance(value, (tuple, list)) or len(value) < 2:
        raise ValueError("A point must have at least x and y coordinates")
    return (float(value[0]), float(value[1]))


def deduplicate(points, *, tolerance=1e-9):
    result = []
    for item in points:
        normalized = point(item)
        if not result or distance(result[-1], normalized) > tolerance:
            result.append(normalized)
    return result


def polyline_length(points):
    points = list(points)
    return sum(distance(a, b) for a, b in zip(points, points[1:]))


def interpolate_polyline(points, t):
    points = list(points)
    if not points:
        raise ValueError("Cannot interpolate an empty polyline")
    if len(points) == 1:
        return point(points[0])
    lengths = [distance(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    if total == 0:
        return point(points[0])
    remaining = max(0, min(1, t)) * total
    for index, segment_length in enumerate(lengths):
        if remaining <= segment_length:
            return lerp(points[index], points[index + 1], remaining / segment_length if segment_length else 0)
        remaining -= segment_length
    return point(points[-1])
