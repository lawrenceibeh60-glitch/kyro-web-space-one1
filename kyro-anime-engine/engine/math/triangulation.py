"""Ear-clipping triangulation for simple, non-self-intersecting polygons."""
from engine.math.polygons import is_clockwise


def triangulate(points):
    points = list(points)
    if len(points) < 3:
        return []
    if len(points) == 3:
        return [(0, 2, 1) if is_clockwise(points) else (0, 1, 2)]
    indices = list(range(len(points)))
    if is_clockwise(points):
        indices.reverse()
    result = []
    guard = len(indices) ** 2
    while len(indices) > 3 and guard:
        guard -= 1
        found = False
        for offset, current in enumerate(indices):
            previous, following = indices[offset - 1], indices[(offset + 1) % len(indices)]
            a, b, c = points[previous], points[current], points[following]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if cross <= 1e-12:
                continue
            if any(
                _inside_triangle(points[index], a, b, c)
                for index in indices if index not in {previous, current, following}
            ):
                continue
            result.append((previous, current, following))
            del indices[offset]
            found = True
            break
        if not found:
            raise ValueError("Polygon cannot be triangulated; check for self-intersections or duplicate points")
    if len(indices) == 3:
        result.append(tuple(indices))
    return result


def _inside_triangle(point, a, b, c):
    def cross(p1, p2, p3):
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    values = (cross(a, b, point), cross(b, c, point), cross(c, a, point))
    return all(value >= -1e-12 for value in values)
