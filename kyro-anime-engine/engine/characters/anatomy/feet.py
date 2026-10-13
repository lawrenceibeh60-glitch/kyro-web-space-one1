"""Foot outline and toe landmarks."""


def foot_shape(ankle, length, height, direction=1):
    if length <= 0 or height <= 0 or direction not in (-1, 1):
        raise ValueError("Invalid foot dimensions or direction")
    x, y = ankle
    return [(x, y), (x + direction * length * 0.3, y + height),
            (x + direction * length, y + height * 0.8),
            (x + direction * length, y + height * 0.4)]
