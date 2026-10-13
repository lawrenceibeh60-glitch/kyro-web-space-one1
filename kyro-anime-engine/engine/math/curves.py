"""Interpolation and sampling for common animation curves."""
from engine.math.numerical import clamp, lerp


def cubic_bezier(p0, p1, p2, p3, t):
    t = clamp(t, 0.0, 1.0)
    u = 1 - t
    return u ** 3 * p0 + 3 * u ** 2 * t * p1 + 3 * u * t ** 2 * p2 + t ** 3 * p3


def sample(function, start=0.0, end=1.0, steps=32):
    if steps < 1:
        raise ValueError("steps must be at least 1")
    return [function(lerp(start, end, index / steps)) for index in range(steps + 1)]


def cubic_bezier_point(p0, p1, p2, p3, t):
    return tuple(cubic_bezier(p0[i], p1[i], p2[i], p3[i], t) for i in range(len(p0)))
