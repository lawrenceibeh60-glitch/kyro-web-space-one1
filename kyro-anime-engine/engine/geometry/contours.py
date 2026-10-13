"""Contour cleanup, orientation and simplification."""
from engine.math.polygons import signed_area
from engine.math.vectors import distance


def clean(points, *, tolerance=1e-9, closed=True):
    result = []
    for point in points:
        point = tuple(point[:2])
        if not result or distance(point, result[-1]) > tolerance:
            result.append(point)
    if closed and len(result) > 1 and distance(result[0], result[-1]) <= tolerance:
        result.pop()
    return result


def orient(points, *, clockwise=False):
    points = list(points)
    if (signed_area(points) < 0) != clockwise:
        points.reverse()
    return points


def simplify(points, tolerance):
    points = list(points)
    if len(points) <= 2:
        return points
    start, end = points[0], points[-1]
    dx, dy = end[0] - start[0], end[1] - start[1]
    denominator = dx * dx + dy * dy
    max_distance, split = -1, None
    for index, point in enumerate(points[1:-1], 1):
        t = 0 if denominator == 0 else max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denominator))
        projected = (start[0] + t * dx, start[1] + t * dy)
        deviation = distance(point, projected)
        if deviation > max_distance:
            max_distance, split = deviation, index
    if max_distance > tolerance:
        return simplify(points[:split + 1], tolerance)[:-1] + simplify(points[split:], tolerance)
    return [start, end]
