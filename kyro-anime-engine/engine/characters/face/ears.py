"""Ear silhouette landmark generation."""


def ear_shape(base, width, height, side=1):
    if width <= 0 or height <= 0 or side not in (-1, 1):
        raise ValueError("Invalid ear dimensions or side")
    x, y = base
    return [(x, y), (x + side * width * 0.8, y - height * 0.35),
            (x + side * width, y - height), (x + side * width * 0.35, y - height * 0.8)]
