"""Deterministic particle emission for frame-based rendering."""
import math


def particle(effect_id, index, frame, *, origin=(0, 0), count=36, speed=1, seed=0):
    stable = sum(ord(char) for char in str(effect_id)) + index * 7919 + seed * 104729
    angle = ((stable * 0.618033988749895) % 1) * math.tau
    birth = stable % 24
    age = max(0, frame - birth)
    radius = age * speed * (8 + (stable % 13))
    return {
        "x": origin[0] + math.cos(angle) * radius,
        "y": origin[1] + math.sin(angle) * radius,
        "alpha": max(0.0, 1 - age / 48),
        "size": 1 + (stable % 5),
    }


def emit(effect, frame, *, origin=(0, 0), seed=0):
    count = int(effect.get("count", 36))
    return [particle(effect.get("id", "particles"), index, frame, origin=origin,
                     speed=effect.get("speed", 1), seed=seed)
            for index in range(count)]
