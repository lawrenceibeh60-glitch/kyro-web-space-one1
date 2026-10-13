"""Procedural hand landmark generation."""
import math


def hand_landmarks(wrist, size=1.0, fingers=4):
    if size <= 0 or fingers < 1:
        raise ValueError("size and finger count must be positive")
    x, y = wrist
    palm = (x, y + size * 0.4)
    tips = []
    for index in range(fingers):
        offset = (index - (fingers - 1) / 2) * size * 0.22
        tips.append((x + offset, y + size * (1.2 + 0.15 * (1 - abs(offset) / size))))
    thumb_angle = math.radians(-135)
    tips.append((x + math.cos(thumb_angle) * size * 0.75,
                 y + math.sin(thumb_angle) * size * 0.75))
    return {"wrist": tuple(wrist), "palm": palm, "fingertips": tips}
