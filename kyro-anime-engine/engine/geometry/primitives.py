"""Generators for common 2D drawing primitives."""
import math


def line(start, end):
    return [tuple(start[:2]), tuple(end[:2])]


def rectangle(x, y, width, height):
    return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]


def ellipse(cx, cy, rx, ry=None, *, segments=32):
    if segments < 3:
        raise ValueError("An ellipse requires at least three segments")
    ry = rx if ry is None else ry
    return [
        (cx + rx * math.cos(math.tau * i / segments), cy + ry * math.sin(math.tau * i / segments))
        for i in range(segments)
    ]


def regular_polygon(cx, cy, radius, sides, *, rotation=0):
    if sides < 3:
        raise ValueError("A polygon requires at least three sides")
    return [
        (cx + radius * math.cos(rotation + math.tau * i / sides),
         cy + radius * math.sin(rotation + math.tau * i / sides))
        for i in range(sides)
    ]
