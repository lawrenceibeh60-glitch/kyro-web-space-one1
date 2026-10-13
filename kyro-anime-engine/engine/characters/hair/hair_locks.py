"""Hair lock curve construction."""
import math


def lock_curve(root, length, angle=-90, curl=0, samples=12):
    if length < 0 or samples < 2:
        raise ValueError("length must be non-negative and samples >= 2")
    result = []
    base = math.radians(angle)
    for index in range(samples):
        t = index / (samples - 1)
        theta = base + curl * t * math.pi / 180
        result.append((root[0] + math.cos(theta) * length * t,
                       root[1] + math.sin(theta) * length * t))
    return result
