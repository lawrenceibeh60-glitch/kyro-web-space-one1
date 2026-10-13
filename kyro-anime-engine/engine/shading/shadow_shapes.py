"""Project a 2D contour along a directional light vector."""


def cast_shadow(points, light_direction, *, distance=100):
    dx, dy = light_direction[:2]
    magnitude = (dx * dx + dy * dy) ** 0.5
    if magnitude == 0:
        raise ValueError("Light direction must be non-zero")
    dx, dy = dx / magnitude, dy / magnitude
    return [(point[0] + dx * distance, point[1] + dy * distance) for point in points]
