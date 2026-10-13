"""Generate evenly spaced eyelash strokes."""


def lash_strokes(origin, direction, count=5, length=0.12, spread=0.5):
    if count < 0 or length < 0:
        raise ValueError("count and length must be non-negative")
    dx, dy = direction
    magnitude = (dx * dx + dy * dy) ** 0.5 or 1
    dx, dy = dx / magnitude, dy / magnitude
    return [((origin[0] + dx * index * spread / max(count - 1, 1),
              origin[1] + dy * index * spread / max(count - 1, 1)),
             (origin[0] + dx * index * spread / max(count - 1, 1) + dx * length,
              origin[1] + dy * index * spread / max(count - 1, 1) + dy * length))
            for index in range(count)]
