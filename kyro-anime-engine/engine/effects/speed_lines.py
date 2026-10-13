"""Generate directional speed-line segments around a focus point."""
import math


def generate(center, *, count=24, radius=180, length=70, angle=0, seed=0):
    if count < 0 or radius < 0 or length < 0:
        raise ValueError("count, radius, and length must be non-negative")
    output = []
    for index in range(count):
        phase = (index * 0.618033988749895 + seed * 0.137) % 1
        direction = angle + (phase - 0.5) * math.pi
        radial = radius * (0.35 + ((index * 0.754877666) % 0.65))
        x, y = center[0] + math.cos(direction) * radial, center[1] + math.sin(direction) * radial
        output.append(((x, y), (x + math.cos(direction) * length, y + math.sin(direction) * length)))
    return output
