"""Deterministic sinusoidal distortion fields for stylized effects."""
import math


def displace(point, frame, *, amplitude=4, frequency=0.04, phase=0):
    x, y = point[:2]
    return (
        x + math.sin(y * frequency + frame + phase) * amplitude,
        y + math.sin(x * frequency + frame * 0.73 + phase) * amplitude,
    )


def distort_points(points, frame, **options):
    return [displace(point, frame, **options) for point in points]
