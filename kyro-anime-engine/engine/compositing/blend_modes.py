"""Per-channel blend modes for normalized RGB values."""


def blend(base, source, mode="normal"):
    if mode == "normal":
        return tuple(source)
    if mode == "multiply":
        return tuple(a * b for a, b in zip(base, source))
    if mode == "screen":
        return tuple(1 - (1 - a) * (1 - b) for a, b in zip(base, source))
    if mode == "add":
        return tuple(min(1, a + b) for a, b in zip(base, source))
    if mode == "subtract":
        return tuple(max(0, a - b) for a, b in zip(base, source))
    if mode == "difference":
        return tuple(abs(a - b) for a, b in zip(base, source))
    if mode == "overlay":
        return tuple(2 * a * b if a < 0.5 else 1 - 2 * (1 - a) * (1 - b)
                     for a, b in zip(base, source))
    raise ValueError(f"Unsupported blend mode: {mode}")
