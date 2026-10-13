"""Minimal stylized nose landmarks."""


def nose_shape(center, width, height, style="line"):
    if width <= 0 or height <= 0:
        raise ValueError("Nose dimensions must be positive")
    x, y = center
    if style == "line":
        return [(x, y - height / 2), (x - width / 2, y + height / 2), (x + width / 2, y + height / 2)]
    if style == "dot":
        return {"center": (x, y + height / 2), "radius": width / 2}
    raise ValueError(f"Unsupported nose style: {style}")
