"""Common 2D segment, line, and circle intersection tests."""
from engine.math.vectors import cross2, subtract


def segment_intersection(a, b, c, d, *, epsilon=1e-9):
    r, s = subtract(b, a), subtract(d, c)
    denominator = cross2(r, s)
    q_minus_p = subtract(c, a)
    if abs(denominator) <= epsilon:
        return None
    t = cross2(q_minus_p, s) / denominator
    u = cross2(q_minus_p, r) / denominator
    if -epsilon <= t <= 1 + epsilon and -epsilon <= u <= 1 + epsilon:
        return (a[0] + t * r[0], a[1] + t * r[1])
    return None


def point_on_segment(point, a, b, *, epsilon=1e-9):
    v, w = subtract(b, a), subtract(point, a)
    cross = cross2(v, w)
    return abs(cross) <= epsilon and -epsilon <= w[0] * v[0] + w[1] * v[1] <= v[0] ** 2 + v[1] ** 2 + epsilon


def circle_intersects(a, radius_a, b, radius_b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= (radius_a + radius_b) ** 2
