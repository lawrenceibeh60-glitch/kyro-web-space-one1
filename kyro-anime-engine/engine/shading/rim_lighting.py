"""Fresnel-like rim light intensity."""


def intensity(normal, view_direction, *, power=3, strength=1):
    if power <= 0:
        raise ValueError("power must be positive")
    norm = lambda vector: tuple(value / (sum(item * item for item in vector) ** 0.5)
                                for value in vector) if any(vector) else tuple(0 for _ in vector)
    n, v = norm(normal), norm(view_direction)
    cosine = max(-1.0, min(1.0, sum(a * b for a, b in zip(n, v))))
    return max(0.0, min(1.0, strength * (1 - abs(cosine)) ** power))
