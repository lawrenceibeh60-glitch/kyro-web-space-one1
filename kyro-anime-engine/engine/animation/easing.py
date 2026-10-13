"""Named easing functions and cubic Bezier easing."""
import math


def apply(name, t):
    t = max(0.0, min(1.0, float(t)))
    if isinstance(name, dict):
        bezier = name.get("bezier")
        if isinstance(bezier, (list, tuple)) and len(bezier) == 4:
            return cubic_bezier_ease(t, *bezier)
        raise ValueError("Bezier easing requires four control values")
    functions = {
        "linear": lambda x: x,
        "hold": lambda x: 0.0,
        "ease_in": lambda x: x * x,
        "ease_out": lambda x: 1 - (1 - x) ** 2,
        "ease_in_out": lambda x: 2 * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 2 / 2,
        "sine_in": lambda x: 1 - math.cos(x * math.pi / 2),
        "sine_out": lambda x: math.sin(x * math.pi / 2),
        "sine_in_out": lambda x: -(math.cos(math.pi * x) - 1) / 2,
    }
    try:
        return functions[name](t)
    except KeyError as error:
        raise ValueError(f"Unknown easing: {name}") from error


def cubic_bezier_ease(t, x1, y1, x2, y2, *, iterations=16):
    def coordinate(u, a, b):
        inverse = 1 - u
        return 3 * inverse * inverse * u * a + 3 * inverse * u * u * b + u ** 3
    low, high = 0.0, 1.0
    for _ in range(iterations):
        mid = (low + high) / 2
        if coordinate(mid, x1, x2) < t:
            low = mid
        else:
            high = mid
    return coordinate((low + high) / 2, y1, y2)
