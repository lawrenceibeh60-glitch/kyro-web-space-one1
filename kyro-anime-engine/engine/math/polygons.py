"""Polygon area, centroid, winding and containment operations."""


def signed_area(points):
    points = list(points)
    if len(points) < 3:
        return 0.0
    return 0.5 * sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )


def area(points):
    return abs(signed_area(points))


def is_clockwise(points):
    return signed_area(points) < 0


def centroid(points):
    points = list(points)
    twice_area = signed_area(points) * 2
    if len(points) < 3 or twice_area == 0:
        if not points:
            return None
        return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
    x_sum = y_sum = 0.0
    for i, point in enumerate(points):
        next_point = points[(i + 1) % len(points)]
        cross = point[0] * next_point[1] - next_point[0] * point[1]
        x_sum += (point[0] + next_point[0]) * cross
        y_sum += (point[1] + next_point[1]) * cross
    return (x_sum / (3 * twice_area), y_sum / (3 * twice_area))


def contains(points, point):
    x, y = point
    inside = False
    points = list(points)
    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]
        if (a[1] > y) != (b[1] > y):
            crossing_x = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < crossing_x:
                inside = not inside
    return inside
