"""Stylized head contour generator."""
import math


def head_outline(center, width, height, segments=32, jaw_taper=0.72):
    if width <= 0 or height <= 0 or segments < 3 or not 0 < jaw_taper <= 1:
        raise ValueError("Invalid head dimensions")
    cx, cy = center
    points = []
    for index in range(segments):
        angle = 2 * math.pi * index / segments
        lower = max(0.0, math.sin(angle))
        scale_x = 1 - lower * (1 - jaw_taper)
        points.append((cx + math.cos(angle) * width * scale_x / 2,
                       cy + math.sin(angle) * height / 2))
    return points
