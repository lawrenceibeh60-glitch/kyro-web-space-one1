"""Timed screen flash alpha envelopes."""
from engine.effects.effect_timing import progress


def alpha(effect, frame):
    t = progress(effect, frame)
    if t is None:
        return 0.0
    return max(0.0, min(1.0, effect.get("intensity", 1.0))) * (1 - t)


def flash_color(effect, frame):
    return effect.get("color", "#ffffff"), alpha(effect, frame)
