"""Small dependency-free vector operations for 2D and 3D geometry."""
import math


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def scale(vector, amount):
    return tuple(value * amount for value in vector)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def length(vector):
    return math.sqrt(dot(vector, vector))


def normalize(vector):
    magnitude = length(vector)
    return tuple(0.0 for _ in vector) if magnitude == 0 else scale(vector, 1 / magnitude)


def distance(a, b):
    return length(subtract(a, b))


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def perpendicular(vector):
    return (-vector[1], vector[0])


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))
