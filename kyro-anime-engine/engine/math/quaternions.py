"""Quaternion helpers for 3D orientation and interpolation."""
import math


def normalize(q):
    magnitude = math.sqrt(sum(value * value for value in q))
    return (1.0, 0.0, 0.0, 0.0) if magnitude == 0 else tuple(value / magnitude for value in q)


def multiply(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def from_axis_angle(axis, radians):
    length = math.sqrt(sum(component * component for component in axis))
    if length == 0:
        raise ValueError("Rotation axis must be non-zero")
    scale = math.sin(radians / 2) / length
    return (math.cos(radians / 2), *(component * scale for component in axis))


def slerp(a, b, t):
    a, b = normalize(a), normalize(b)
    cosine = sum(x * y for x, y in zip(a, b))
    if cosine < 0:
        b = tuple(-value for value in b)
        cosine = -cosine
    if cosine > 0.9995:
        return normalize(tuple(x + t * (y - x) for x, y in zip(a, b)))
    theta = math.acos(max(-1, min(1, cosine)))
    factor = math.sin(theta)
    left, right = math.sin((1 - t) * theta) / factor, math.sin(t * theta) / factor
    return tuple(left * x + right * y for x, y in zip(a, b))
