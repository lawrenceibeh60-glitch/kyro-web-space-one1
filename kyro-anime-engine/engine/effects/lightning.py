"""Seeded jagged lightning bolt geometry."""
import random


def bolt(start, end, *, segments=12, displacement=24, seed=0):
    if segments < 1 or displacement < 0:
        raise ValueError("segments must be positive and displacement non-negative")
    rng = random.Random(seed)
    points = []
    for index in range(segments + 1):
        t = index / segments
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t
        if index not in (0, segments):
            x += rng.uniform(-displacement, displacement)
            y += rng.uniform(-displacement, displacement)
        points.append((x, y))
    return points


def branches(points, *, count=2, seed=0):
    rng = random.Random(seed)
    result = []
    for _ in range(max(0, count)):
        if len(points) < 2:
            break
        origin = points[rng.randrange(len(points) - 1)]
        end = (origin[0] + rng.uniform(-50, 50), origin[1] + rng.uniform(20, 80))
        result.append(bolt(origin, end, segments=5, displacement=8, seed=rng.randrange(1 << 30)))
    return result
