"""Arbitrary-degree Bezier curve evaluation and adaptive sampling."""
from engine.math.vectors import lerp


def evaluate(points, t):
    work = [tuple(point) for point in points]
    if not work:
        raise ValueError("A Bezier curve requires control points")
    t = max(0.0, min(1.0, t))
    while len(work) > 1:
        work = [lerp(work[index], work[index + 1], t) for index in range(len(work) - 1)]
    return work[0]


def sample(points, segments=32):
    if segments < 1:
        raise ValueError("segments must be at least 1")
    return [evaluate(points, i / segments) for i in range(segments + 1)]
