"""Pupil positioning within the iris."""


def pupil_position(center, radius, gaze=(0, 0)):
    if radius <= 0:
        raise ValueError("Iris radius must be positive")
    gx, gy = gaze
    length = (gx * gx + gy * gy) ** 0.5
    limit = radius * 0.45
    if length > 1:
        gx, gy = gx / length, gy / length
    return center[0] + gx * limit, center[1] + gy * limit
