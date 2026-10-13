"""Linear and radial color gradient interpolation."""
from engine.shading.color_management import hex_to_rgb, rgb_to_hex


def interpolate_color(start, end, t):
    a = hex_to_rgb(start) if isinstance(start, str) else start
    b = hex_to_rgb(end) if isinstance(end, str) else end
    return tuple(round(x + (y - x) * max(0, min(1, t))) for x, y in zip(a, b))


def linear_gradient(start_color, end_color, steps):
    if steps < 1:
        raise ValueError("steps must be positive")
    return [rgb_to_hex(interpolate_color(start_color, end_color, i / max(steps - 1, 1)))
            for i in range(steps)]


def radial_factor(point, center, radius):
    if radius <= 0:
        raise ValueError("radius must be positive")
    import math
    return max(0.0, 1 - math.dist(point, center) / radius)
