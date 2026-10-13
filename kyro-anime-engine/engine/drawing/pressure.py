"""Pressure response curves for tablet and touch input."""
from engine.math.numerical import clamp


def normalize_pressure(value, *, fallback=1.0):
    if value is None:
        value = fallback
    return clamp(float(value), 0.0, 1.0)


def apply_pressure(base_width, pressure, *, minimum=0.08, gamma=1.0):
    if base_width < 0 or gamma <= 0:
        raise ValueError("base_width must be non-negative and gamma positive")
    pressure = normalize_pressure(pressure)
    return base_width * (minimum + (1 - minimum) * pressure ** gamma)


def pressure_points(points, base_width, **options):
    return [(point[0], point[1], apply_pressure(base_width, point[2] if len(point) > 2 else 1, **options))
            for point in points]
