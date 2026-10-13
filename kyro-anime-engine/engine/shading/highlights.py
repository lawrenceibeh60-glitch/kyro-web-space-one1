"""Specular highlight response for stylized materials."""


def specular(normal, light_direction, view_direction, *, shininess=24):
    if shininess <= 0:
        raise ValueError("shininess must be positive")
    length = lambda vector: sum(component * component for component in vector) ** 0.5
    normalize = lambda vector: tuple(value / length(vector) for value in vector) if length(vector) else tuple(0 for _ in vector)
    n, l, v = normalize(normal), normalize(light_direction), normalize(view_direction)
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    reflected = tuple(2 * dot(n, l) * x - y for x, y in zip(n, l))
    return max(0.0, dot(reflected, v)) ** shininess
