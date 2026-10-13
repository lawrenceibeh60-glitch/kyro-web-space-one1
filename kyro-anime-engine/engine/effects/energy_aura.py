"""Generate deterministic animated aura rings and sparks."""
import math


def aura(center, frame, *, radius=64, count=12, intensity=1, seed=0):
    result = []
    for index in range(max(0, count)):
        phase = (index / max(count, 1)) * math.tau + frame * 0.12 + seed
        distance = radius * (0.8 + 0.2 * math.sin(phase * 2))
        result.append({
            "x": center[0] + math.cos(phase) * distance,
            "y": center[1] + math.sin(phase) * distance,
            "size": max(0, intensity * (2 + math.sin(phase * 3))),
            "alpha": max(0, min(1, intensity * (0.5 + 0.5 * math.sin(phase)))),
        })
    return result
