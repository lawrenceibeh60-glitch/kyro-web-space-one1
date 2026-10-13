"""Shoulder endpoints and range-of-motion helpers."""
import math


def shoulder_points(center, width):
    if width <= 0:
        raise ValueError("Shoulder width must be positive")
    x, y = center
    return (x - width / 2, y), (x + width / 2, y)


def arm_endpoint(origin, length, angle_degrees):
    angle = math.radians(angle_degrees)
    return origin[0] + length * math.cos(angle), origin[1] + length * math.sin(angle)
