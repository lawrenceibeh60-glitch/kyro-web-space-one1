"""Neck landmark geometry."""


def neck_shape(center, width, height):
    if width <= 0 or height <= 0:
        raise ValueError("Neck dimensions must be positive")
    x, y = center
    return [(x - width / 2, y), (x + width / 2, y),
            (x + width * 0.4, y + height), (x - width * 0.4, y + height)]
