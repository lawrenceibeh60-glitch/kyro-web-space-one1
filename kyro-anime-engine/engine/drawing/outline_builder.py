"""Construct a simple variable-width outline around a polyline."""
import math


def outline(points, width):
    points = [tuple(point[:2]) for point in points]
    if width < 0:
        raise ValueError("width must be non-negative")
    if len(points) < 2:
        return []
    left, right = [], []
    for index, point in enumerate(points):
        before = points[max(0, index - 1)]
        after = points[min(len(points) - 1, index + 1)]
        dx, dy = after[0] - before[0], after[1] - before[1]
        length = math.hypot(dx, dy)
        if length == 0:
            nx, ny = 0.0, 0.0
        else:
            nx, ny = -dy / length, dx / length
        left.append((point[0] + nx * width / 2, point[1] + ny * width / 2))
        right.append((point[0] - nx * width / 2, point[1] - ny * width / 2))
    return left + right[::-1]
