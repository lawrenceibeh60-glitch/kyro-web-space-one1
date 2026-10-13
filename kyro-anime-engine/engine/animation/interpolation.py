"""Interpolate scalar, tuple, and supported discrete animation values."""
from engine.animation.easing import apply as ease


def interpolate(a, b, t):
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, (str, bool)) or isinstance(b, (str, bool)):
        return a if t < 1 else b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * t
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
        return type(a)(interpolate(x, y, t) for x, y in zip(a, b))
    return a if t < 1 else b


def evaluate_track(keyframes, frame, default=0):
    if not keyframes:
        return default
    keys = sorted(keyframes, key=lambda item: item["t"])
    if frame <= keys[0]["t"]:
        return keys[0]["v"]
    for left, right in zip(keys, keys[1:]):
        if frame <= right["t"]:
            if left.get("ease") == "hold":
                return left["v"]
            t = (frame - left["t"]) / (right["t"] - left["t"])
            return interpolate(left["v"], right["v"], ease(left.get("ease", "linear"), t))
    return keys[-1]["v"]
