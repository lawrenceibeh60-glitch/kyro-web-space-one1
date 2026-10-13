"""Numerical helpers used by animation and geometry code."""
import math


def clamp(value, low, high):
    if low > high:
        raise ValueError("low must not exceed high")
    return min(high, max(low, value))


def lerp(a, b, t):
    return a + (b - a) * t


def inverse_lerp(a, b, value):
    return 0.0 if a == b else (value - a) / (b - a)


def smoothstep(a, b, value):
    t = clamp(inverse_lerp(a, b, value), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def wrap(value, low, high):
    span = high - low
    if span <= 0:
        raise ValueError("high must exceed low")
    return low + (value - low) % span


def nearly_equal(a, b, *, tolerance=1e-9):
    return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)
