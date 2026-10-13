"""Axis-aligned 2D bounds represented as (min_x, min_y, max_x, max_y)."""


def from_points(points):
    points = list(points)
    if not points:
        return None
    return (min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points))


def intersects(a, b):
    return a is not None and b is not None and a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def contains(bounds, point):
    return bounds is not None and bounds[0] <= point[0] <= bounds[2] and bounds[1] <= point[1] <= bounds[3]


def union(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def expand(bounds, amount):
    return (bounds[0] - amount, bounds[1] - amount, bounds[2] + amount, bounds[3] + amount)


def area(bounds):
    return max(0, bounds[2] - bounds[0]) * max(0, bounds[3] - bounds[1])
