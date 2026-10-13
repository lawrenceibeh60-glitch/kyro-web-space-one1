"""Stylized fold lines radiating from a pinch point."""
import math


def fold_lines(origin, count=5, length=0.2, spread=math.pi / 2):
    if count < 0 or length < 0:
        raise ValueError("count and length must be non-negative")
    if count == 0:
        return []
    return [(tuple(origin), (origin[0] + length * math.cos(-spread / 2 + spread * i / max(count - 1, 1)),
                             origin[1] + length * math.sin(-spread / 2 + spread * i / max(count - 1, 1))))
            for i in range(count)]
