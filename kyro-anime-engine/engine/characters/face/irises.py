"""Iris rings and radial detail points."""
import math


def iris_points(center, radius, count=16):
    if radius <= 0 or count < 3:
        raise ValueError("Iris radius must be positive and count >= 3")
    return [(center[0] + radius * math.cos(2 * math.pi * i / count),
             center[1] + radius * math.sin(2 * math.pi * i / count)) for i in range(count)]
